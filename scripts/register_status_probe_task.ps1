# Register-ScheduledTask for verdmat-daily-status-probe. Run once, from an
# elevated PowerShell (admin), to install the scheduled task. Re-running is
# idempotent — it overwrites the existing definition.
#
# NOT YET REGISTERED — cc63 HALT: design + dry-run done, activation awaits go.
#
# Schedule:    DAILY 07:30 local (GMT) — after every nightly (delta 01:00,
#              myigloo 02:00, sales-refresh 02:30, backup 03:00, lifecycle
#              06:00) and the Sunday weeklies (04:00/04:30/05:00), so it reads
#              the night's final LastTaskResult values, never mid-run ones.
# Wake:        YES.  Run whether user logged in: YES (S4U, no stored password).
# Retry:       NONE — the probe itself failing shows up as its own
#              LastTaskResult next morning.
#
# The task runs scripts/verdmat_status_probe.ps1 (no flags): reads
# LastTaskResult of all verdmat-* tasks + the terminal line of the newest
# night_*.log / myigloo_night_*.log and appends ONE summary line to
# D:\verdmat_status.log (+ a loud !! line when anything is off).

$ErrorActionPreference = 'Stop'

$taskName = 'verdmat-daily-status-probe'
$psExe    = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$scriptPs = 'D:\verdmat-is\app\scripts\verdmat_status_probe.ps1'
$workDir  = 'D:\verdmat-is\app'

if (-not (Test-Path $scriptPs)) {
    throw "Probe script missing: $scriptPs"
}

$action = New-ScheduledTaskAction `
    -Execute $psExe `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPs`"" `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Daily -At '07:30'

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

# S4U principal — same locked pattern as the other verdmat tasks (Password
# principal fails silently; S4U needs no stored credential and suffices:
# local disk reads + one local file append). RunLevel Limited.
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
        -Description 'verdmat.is daily status probe: LastTaskResult of all verdmat-* tasks + nightly chain-log terminal lines -> one summary line appended to D:\verdmat_status.log (+ loud line if anything is not 0/3). Daily 07:30 GMT.' `
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
