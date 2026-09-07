# register_verdvakt_refresh_task.ps1 — cc193 (2026-09-07). Keyrist EINU SINNI úr HÆKKUÐU PowerShell
# (Danni, HALT B). Endurkeyrsla er idempotent. -Thurrt = þurrpróf, skráir ekkert.
#
# VERK:  verdmat_verdvakt_refresh — D:\verdmat-is\verdmat-ai\scripts\cc188_verdvakt_refresh.py --revalidate
#        gegnum scripts\cc193_keyra_verk.ps1 -Verk verdvakt_refresh (logg D:\verdmat-is\logs\verdvakt_refresh.log).
#        Athuganaskrá (verdvakt_skra_athuganir) → REFRESH CONCURRENTLY á MV-unum þremur → POST
#        /api/verdvakt/endurnyja með ENDURNYJA_LYKILL (keyrarinn hleður hann úr D:\env.local í umhverfið;
#        verdmat-ai er ÓSNERT á kóðahlið) svo /verdvaktin og forsíðukassinn hendi cache strax (annars 1 klst TTL).
#
# TÍMAR (TVEIR triggerar — mælt í Task Scheduler-atburðaloggi 02.–07.09):
#   06:45 — eftir nætur-scrape-keðjuna (verdmat-nightly-delta, lauk 02:40–04:55 sex nætur; ber verð og
#           last_seen_at) og eftir sales-refresh 02:30 (kaupskrármátun). cc188-tillagan 06:45 STENST gegn
#           þeirri mælingu. Keyrarinn ber biðhlið á delta (≤90 mín) fyrir hægar nætur (8 klst þak keðjunnar).
#   18:15 — eftir verdmat-daily-lifecycle-sweep (06:00), sem lauk 17:18 / 17:58 / 17:18 / 14:22 og hitti
#           12 klst þakið 18:00 þann 02.09; sópunin skrifar withdrawn_confirmed (farnar-ásinn). Án seinni
#           keyrslunnar birtast afsölur dagsins 13 klst seint. Strikaðu þennan trigger út (línan merkt [2])
#           ef ein keyrsla á dag dugar — ekkert annað breytist.
#   Keyrslutími mældur 07.09: 43 s (athuganaskrá 415 nýjar/382 uppf., breytingar-MV 35 s).
# ÞAK:   2 klst (biðhlið + keyrsla). IgnoreNew. WakeToRun + StartWhenAvailable.
# LOGON: S4U (Password-principal fellur þögult — CLAUDE.md). RunLevel Limited.
# ROLLBACK: Unregister-ScheduledTask -TaskName verdmat_verdvakt_refresh -Confirm:$false
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'

$TaskName = 'verdmat_verdvakt_refresh'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\verdmat-ai\scripts\cc188_verdvakt_refresh.py'
$WorkDir  = 'D:\verdmat-is\verdmat-ai'

foreach ($p in @($PS, $Keyrari, $Python, $Skrift)) { if (-not (Test-Path $p)) { throw "vantar: $p" } }

$action = New-ScheduledTaskAction -Execute $PS `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk verdvakt_refresh') `
    -WorkingDirectory $WorkDir
$triggers = @(
    (New-ScheduledTaskTrigger -Daily -At 06:45),   # [1] eftir nætur-scrape
    (New-ScheduledTaskTrigger -Daily -At 18:15)    # [2] eftir lifecycle-sweep — má strika út
)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"aðgerð:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
foreach ($t in $triggers) { "trigger:   Daily $($t.StartBoundary)" }
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"þak:       $($settings.ExecutionTimeLimit)  instances=$($settings.MultipleInstances)  wake=$($settings.WakeToRun)"
if ($Thurrt) { "ÞURRPRÓF — ekkert skráð."; exit 0 }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskráði eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Principal $principal -Settings $settings `
        -Description 'cc188/cc193: Verdvaktin refresh (athuganaskra + 3 MV + revalidate); 06:45 eftir nightly-delta, 18:15 eftir lifecycle-sweep; logg D:\verdmat-is\logs\verdvakt_refresh.log' `
        -ErrorAction Stop | Out-Null
    "SKRÁÐ $TaskName"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    "næsta keyrsla: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRÁNING FÉLL: $($_.Exception.Message)"
    exit 1
}
