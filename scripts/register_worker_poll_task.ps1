# register_worker_poll_task.ps1 — cc193 (2026-09-07). Keyrist EINU SINNI úr HÆKKUÐU
# PowerShell (Danni, HALT B). Endurkeyrsla er idempotent (eldra verk fellt fyrst).
#   -Thurrt : smíðar verkhlutina og prentar, SKRÁIR EKKERT (þurrpróf lotunnar, án elevation).
#
# VERK:  verdmat_worker_poll — fable_worker.py --once --leyfa-fable --hamark 3 --adeins-live
#        gegnum scripts\cc193_keyra_verk.ps1 -Verk worker_poll (logg D:\verdmat-is\logs\worker_poll.log).
# TÍMI:  á 5 mín fresti, allan sólarhringinn (Once-trigger 00:00 + endurtekning 5 mín, ótímabundið).
# HVERS VEGNA: salan er opin (cc185/cc186: fyrsta live-keðjan 07.09) og greidd pöntun er umboðið —
#        workerinn fær STANDANDI Fable-heimild á scheduler (DECISIONS-tillaga cc193) með girðingum:
#        (a) aðeins status=paid ∧ paddle_env=live  (b) ≤3 Fable-köll per poll, umfram bíður (bókað)
#        (c) kill-switch D:\verdmat-is\STOPP_FABLE  (d) póstur + idempotens (email_sent_at) óbreytt.
# ÞAK:   50 mín (3 pantanir × ~8 mín mælt á ea5e517a 484 s + póstur); MultipleInstances=IgnoreNew
#        svo 5-mín-trigger tvíræsir aldrei ofan í keyrslu (FOR UPDATE SKIP LOCKED ver röðina líka).
# LOGON: S4U (Password-principal fellur þögult — CLAUDE.md). RunLevel Limited. Enginn WakeToRun
#        (5-mín verk á ekki að vekja vél; AC-svefn er hvort eð er af).
# ROLLBACK: Unregister-ScheduledTask -TaskName verdmat_worker_poll -Confirm:$false
#           (eða kill-switch án afskráningar: New-Item D:\verdmat-is\STOPP_FABLE)
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'

$TaskName = 'verdmat_worker_poll'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\app\scripts\fable_worker.py'
$WorkDir  = 'D:\verdmat-is\app'

foreach ($p in @($PS, $Keyrari, $Python, $Skrift)) { if (-not (Test-Path $p)) { throw "vantar: $p" } }

$action = New-ScheduledTaskAction -Execute $PS `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk worker_poll') `
    -WorkingDirectory $WorkDir
$start   = (Get-Date -Hour 0 -Minute 0 -Second 0 -Millisecond 0)
$trigger = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 50) `
    -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"aðgerð:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
"trigger:   Once $($trigger.StartBoundary) + endurtekning $($trigger.Repetition.Interval) (duration='$($trigger.Repetition.Duration)' = ótímabundið)"
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"þak:       $($settings.ExecutionTimeLimit)  instances=$($settings.MultipleInstances)"
if ($Thurrt) { "ÞURRPRÓF — ekkert skráð."; exit 0 }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskráði eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'cc193: Fable-worker pollun 5 min; --leyfa-fable --hamark 3 --adeins-live; kill-switch D:\verdmat-is\STOPP_FABLE; logg D:\verdmat-is\logs\worker_poll.log' `
        -ErrorAction Stop | Out-Null
    "SKRÁÐ $TaskName"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    "næsta keyrsla: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRÁNING FÉLL: $($_.Exception.Message)"
    exit 1
}
