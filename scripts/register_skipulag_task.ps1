# register_skipulag_task.ps1 — cc361 (21.11.2026). TILLAGA: skráir verdmat-weekly-skipulag, mánudaga 19:30 UTC.
# Idempotent; -Thurrt skráir ekkert. Skráning er SÉR SKREF með samþykki eiganda (flokkur B), ekki hluti af migration.
#
# VERK:   vikulegur innlestur skipulagsmála -> public.skipulag_mal: cc193_keyra_verk.ps1 -Verk skipulag
#         -> C:\Python314\python.exe scripts\skipulag_innlestur.py --beita (færsla í pipeline_runs, run_type skipulag_vikulegt).
# TÍMI:   mánudagur 19:30 (vélin á GMT = UTC). Heimildin er endurnýjuð sunnudaga 20:00-22:59 UTC og útflutningurinn er
#         síðasta skref hennar -> ekki sunnudagskvöld. Sópunin keyrir 06:00 til um 18:30 og 07:30-07:45 eru upptekin
#         (status-probe 07:30, utflutt-myndir 07:35, cvakt 07:45), svo mánudagskvöld eftir sópun og fyrir 00:45.
#         verdvakt_refresh 18:15 lýkur á mínútum. Biðhlið keyrarans bíður sópunar ef hún er enn Running (2 mín í senn, 90 mín hámark).
#         Mælt 21.11: lestur heimildar 4,8 s + hlið ~5 s; skrifhluti mælist í --prof (sjá SKIL_CC361).
# ÞAK:    15 mín. StartWhenAvailable: missi vélin mánudagskvöld keyrir verkið þegar hún vaknar (hliðin H3/H4 verja gegn
#         gömlum eða endurteknum útflutningi; tímahlið skriftunnar er EKKI til, svo seinkun yfir 01:00 er möguleg ->
#         þá bíður keyrarinn ekki næturkeðju; innlesturinn snertir engar töflur hennar).
# KÓÐAR:  0 í lagi · 2 hlið féll (gamla taflan stendur, VAKT-VIDVORUN + vaktarpóstur) · 3 villa · 4 heimild næst ekki.
# LOGG:   D:\verdmat-is\logs\skipulag.log (keyrarinn).
# LOGON:  S4U, RunLevel Limited. Skráning S4U krefst stjórnandaréttinda: keyrt í admin-skel.
# BAKFÆRSLA: Unregister-ScheduledTask -TaskName verdmat-weekly-skipulag -Confirm:$false
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'
$TaskName = 'verdmat-weekly-skipulag'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$WorkDir  = 'D:\verdmat-is\app'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\app\scripts\skipulag_innlestur.py'
foreach ($p in @($PS, $Keyrari, $Python, $Skrift, 'D:\verdmat-is\.dbconfig', 'D:\env.local')) { if (-not (Test-Path $p)) { throw "vantar: $p" } }
if (-not (Select-String -Path $Keyrari -Pattern "'skipulag'" -Quiet)) { throw "keyrarinn þekkir ekki -Verk skipulag (ff app main fyrst)" }
$pv = & $Python -c "import sys, psycopg2; print(sys.version.split()[0], psycopg2.__version__.split()[0])"
"python:    $Python -> $pv"

$action = New-ScheduledTaskAction -Execute $PS -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk skipulag') -WorkingDirectory $WorkDir
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '19:30'
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew `
    -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"adgerd:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
"trigger:   Weekly Monday $($trigger.StartBoundary)"
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"thak:      $($settings.ExecutionTimeLimit)  instances=$($settings.MultipleInstances)  wake=$($settings.WakeToRun)  startWhenAvailable=$($settings.StartWhenAvailable)"
if ($Thurrt) { 'ÞURRPRÓF: ekkert skráð.'; exit 0 }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskráði eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'cc361: vikulegur innlestur skipulagsmála í public.skipulag_mal, mánudaga 19:30; logg D:\verdmat-is\logs\skipulag.log' `
        -ErrorAction Stop | Out-Null
    "SKRÁÐ $TaskName"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    'næsta keyrsla: ' + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRÁNING FÉLL: $($_.Exception.Message)"
    exit 1
}
