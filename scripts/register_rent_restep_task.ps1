# Register-ScheduledTask for verdmat-weekly-rent-restep. Run once, from an
# elevated PowerShell (admin), to install the scheduled task. Re-running is
# idempotent — it overwrites the existing definition.
#
# Schedule:    WEEKLY, Sunday 04:30 local (GMT). Half an hour after
#              verdmat-weekly-cpi-reanchor (04:00) so the two monthly-gated
#              engines never overlap; both no-op within seconds most weeks.
# Cadence rationale: HMS publishes leiguvísitala/leiguverðsjá monthly; the
#              DB-side gate (max(leiguvisitala.csv) vs predictions_rent
#              predicted_at anchor) no-ops until a new month appears, then the
#              next Sunday catches it. A missed week costs ~0.1% level staleness.
# Wake:        YES.  Run whether user logged in: YES (S4U, no stored password).
# Retry:       NONE — a failed week is a signal, not something to hammer.
# Working dir: D:\verdmat-is\app
#
# The task runs scripts/monthly_rent_level_restep.py with NO flags: fetch
# leiguvísitala+leiguverðsjá (harvest resolver, WARN+disk-fallback on failure) ->
# gate -> factor guard [0.94,1.06] -> drift metric (leiguverðsjá cell level,
# WARN rail ±6%) -> pre-flight backup -> ONE atomic UPDATE (6 pred cols ×f +
# predicted_at) with rowcount gate. Exit 0 clean (incl. no-op) / 1 error /
# 3 guard abort. Run log: D:\monthly_rent_level_restep.log.

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-weekly-rent-restep'
$pythonExe = 'C:\Python314\python.exe'
$scriptPy  = 'D:\verdmat-is\app\scripts\monthly_rent_level_restep.py'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $pythonExe)) {
    throw "python missing: $pythonExe"
}
if (-not (Test-Path $scriptPy)) {
    throw "Restep script missing: $scriptPy"
}

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $scriptPy `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '04:30'

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# S4U principal — same locked pattern as verdmat-weekly-cpi-reanchor (Password
# principal fails silently; S4U needs no stored credential and suffices: local
# disk + outbound HTTPS + Supabase pooler TLS). RunLevel Limited.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    "Unregistered existing $taskName"
}

try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description 'verdmat.is weekly rent-level restep: fetch HMS leiguvisitala+leiguverdsja -> DB-side gate (no-op until new index month) -> on a real move, drift metric + pre-flight snapshot + one atomic UPDATE (predictions_rent x factor, predicted_at advance). Sunday 04:30 GMT. Exit 0 clean / 1 error / 3 guard abort.' `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -ErrorAction Stop | Out-Null

    "Registered $taskName"
    Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State, Triggers
    "Next run time:"
    (Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime
}
catch {
    "REGISTRATION FAILED: $($_.Exception.Message)"
    exit 1
}
