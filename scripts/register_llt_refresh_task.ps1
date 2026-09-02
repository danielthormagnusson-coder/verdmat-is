# register_llt_refresh_task.ps1 — TILLAGA cc180 (2026-09-02), EKKI KEYRÐ, EKKI SKRÁÐ.
#
# Skráir Task Scheduler-verkið `verdmat-nightly-llt-refresh` sem keyrir
# scripts/cc180_llt_refresh.py: R1-b blöndun last_listing_text (evalue-raðir úr
# frosnu D:\last_listing_text.pkl + lifandi mbl-raðir úr scraper.listings) →
# staging → 6 parity-hlið → atómískt rename-swap → hreinsun eldri ref-árganga.
#
# HVERS VEGNA: lindin frýs aftur við snapshot nema blöndunin keyri reglulega.
# Mælt 02.09: milli 00:17 og 20:18 UTC bættust 60 þinglýstar ágústsölur við
# nefnarann (589 → 649) og 64 nýjar lifandi raðir urðu tiltækar (1.350 → 1.414);
# lifandi taflan bar þær ekki, svo 2026-08-þekjan las 70,7 % í stað 77,9 %.
#
# TÍMASETNING (tillaga): 03:45 daglega — á EFTIR verdmat-nightly-delta (01:00,
# skrifar scraper.listings) og verdmat-daily-sales-refresh (02:30, skrifar
# sales_history), á UNDAN verdmat-nightly-backup? Nei — backup er 03:00 og
# snertir ekki DB-töfluna; 03:45 er laust. Vikukeyrsla dugar líka (sunnud. 03:45)
# ef nætur-swap á 130 MB töflu þykir of mikil umferð; þinglýsingartöfin (p50 41 d
# frá auglýsingu) gerir daglega keyrslu að þægindum, ekki nauðsyn.
#
# FORSENDUR SANNREYNDAR 02.09:
#   python:  C:\Python314\python.exe  (3.14.3, sama og hin verdmat-*-verkin)
#   wd:      D:\verdmat-is\app        (skriftan sys.path-ar scripts\ sjálf)
#   logon:   S4U (password-principal fellur þögult — CLAUDE.md)
#   .dbconfig: UTF-8 m/ BOM, lesin með utf-8-sig í cc180_llt_flip.py
#   runner:  sannreyndur með --no-flip 02.09 20:22 UTC (parity 6/6, _new felld)
#   log:     D:\cc180_llt_refresh.log (append) — vaktaðu "PARITY FALL" / "VILLA"
#
# ÞARF ÁÐUR EN SKRÁÐ: (1) GO frá Danna; (2) ein handkeyrsla án --no-flip sem
# sannreynir flipp+hreinsun lifandi (fyrsta ref_-árgangurinn verður til);
# (3) ákvörðun dag/viku; (4) keyra þessa skrá úr HÆKKUÐU PowerShell.
#
# Rollback verksins: Unregister-ScheduledTask -TaskName verdmat-nightly-llt-refresh -Confirm:$false
# Rollback gagna: cc180_llt_flip.py skrifar cc180_rollback_<tag>.sql fyrir hvert flipp.

$TaskName = 'verdmat-nightly-llt-refresh'
$Python   = 'C:\Python314\python.exe'
$Script   = 'D:\verdmat-is\app\scripts\cc180_llt_refresh.py'
$WorkDir  = 'D:\verdmat-is\app'

if (-not (Test-Path $Python)) { throw "python vantar: $Python" }
if (-not (Test-Path $Script)) { throw "skrifta vantar: $Script" }

$action    = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`"" -WorkingDirectory $WorkDir
$trigger   = New-ScheduledTaskTrigger -Daily -At 03:45
# Vikuútgáfa: $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 03:45
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
               -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Principal $principal -Settings $settings `
  -Description 'cc180: last_listing_text R1-b blondun (scraper.listings -> staging -> parity -> rename-swap)'

Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
