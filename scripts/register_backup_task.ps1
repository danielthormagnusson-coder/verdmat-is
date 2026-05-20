# Register-ScheduledTask for verdmat-nightly-backup. Run once, from an
# elevated PowerShell (admin), to install the scheduled task. Re-running is
# idempotent — it overwrites the existing definition.
#
# Schedule:    Daily at 03:00 local time
# Wake:        YES (laptop wakes from sleep to run)
# Run whether user logged in: YES (uses stored creds via -User/-Password)
# Retry:       3 times, 1-hour interval, on any failure
# Working dir: D:\verdmat-is\app (so any relative paths resolve)
#
# Sources its single command from app/scripts/run_backup.ps1 — that file
# does the actual python invocation + per-run wrapper log.

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-nightly-backup'
$scriptPS1 = 'D:\verdmat-is\app\scripts\run_backup.ps1'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $scriptPS1)) {
    throw "Backup script missing: $scriptPS1"
}

# Build task pieces.
$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPS1`"" `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Daily -At '03:00'

# Wake from sleep + retry on failure + reasonable execution-time limit.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Hours 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Run whether user logged in or not. -RunLevel Highest required for wake/
# whether-logged-in semantics. Will prompt for the current user's password.
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Password `
    -RunLevel Highest

# If task already exists, replace it idempotently.
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    "Unregistered existing $taskName"
}

# Will prompt for password on first registration.
Register-ScheduledTask `
    -TaskName $taskName `
    -Description 'verdmat.is rclone backup to Cloudflare R2 (verdmat-backups). Daily 03:00 local.' `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal

"Registered $taskName"
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State, Triggers
"Next run time:"
(Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime
