# register_nybygging_verkefni_task.ps1 — cc224 (2026-10-09). Keyrist EINU SINNI úr HÆKKUÐU PowerShell
# (Danni). Endurkeyrsla er idempotent. -Thurrt = þurrpróf, skráir ekkert.
#
# VERK:  verdmat_nybygging_verkefni — D:\verdmat-is\app\scripts\cc224_nybygging_verkefni.py --skrifa
#        gegnum scripts\cc193_keyra_verk.ps1 -Verk nybygging_verkefni (logg D:\verdmat-is\logs\nybygging_verkefni.log).
#        Reiknar /nybyggingar (semantic.nybygging_verkefni + nybygging_einingar) og skrifar eina röð í
#        semantic.nybygging_keyrslur (nefnarar + md5). Skrifar aðeins útgáfuna sem skriftan ber (UTGAFA).
#
# TÍMI:  07:00 daglega — eftir nætur-scrape-keðjuna (verdmat-nightly-delta, ber listings/last_seen_at),
#        sales-refresh 02:30 (kaupskrá) og verdmat_verdvakt_refresh 06:45 (Verðvakt v2, lækkanir).
#        Keyrarinn ber biðhlið á verdmat-nightly-delta (≤90 mín) fyrir hægar nætur.
#        Keyrslutími mældur 09.10: ~3 mín (les ~12K einingar, ~20K auglýsingar).
# ÞAK:   1 klst (biðhlið + keyrsla). IgnoreNew. WakeToRun + StartWhenAvailable.
# LOGON: S4U (Password-principal fellur þögult — CLAUDE.md). RunLevel Limited.
# ROLLBACK: Unregister-ScheduledTask -TaskName verdmat_nybygging_verkefni -Confirm:$false
#           (gögnin standa; síðasta keyrsla er í nybygging_keyrslur)
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'

$TaskName = 'verdmat_nybygging_verkefni'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\app\scripts\cc224_nybygging_verkefni.py'
$WorkDir  = 'D:\verdmat-is\app'

foreach ($p in @($PS, $Keyrari, $Python, $Skrift)) { if (-not (Test-Path $p)) { throw "vantar: $p" } }
if (-not (Select-String -Path $Keyrari -Pattern "'nybygging_verkefni'" -Quiet)) { throw "keyrarinn þekkir ekki verkið nybygging_verkefni" }

$action = New-ScheduledTaskAction -Execute $PS `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk nybygging_verkefni') `
    -WorkingDirectory $WorkDir
$trigger   = New-ScheduledTaskTrigger -Daily -At 07:00
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"aðgerð:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
"trigger:   Daily $($trigger.StartBoundary)"
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"þak:       $($settings.ExecutionTimeLimit)  instances=$($settings.MultipleInstances)  wake=$($settings.WakeToRun)"
if ($Thurrt) { "ÞURRPRÓF — ekkert skráð."; exit 0 }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskráði eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'cc224: /nybyggingar (semantic.nybygging_verkefni + einingar + keyrslur); 07:00 eftir nightly-delta og verdvakt_refresh; logg D:\verdmat-is\logs\nybygging_verkefni.log' `
        -ErrorAction Stop | Out-Null
    "SKRÁÐ $TaskName"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    "næsta keyrsla: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRÁNING FÉLL: $($_.Exception.Message)"
    exit 1
}
