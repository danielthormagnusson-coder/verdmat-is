# Register-ScheduledTask for verdmat-nightly-delta. Run once, from an
# elevated PowerShell (admin), to install the scheduled task. Re-running is
# idempotent — it overwrites the existing definition.
#
# DO NOT RUN until the §6-A operational gates are open: full-corpus parse done,
# prime_delta_since.py --confirm done (the chain pre-flight refuses otherwise,
# exit 2 — visible as the task's last result).
#
# Schedule:    Daily at 01:00 local time (§6-A.4 — clears the 03:00 backup window;
#              delta is normally minutes, worst case ~6.7h at the 100-page/mode cap)
# Wake:        YES (wakes from sleep to run; AC sleep is disabled anyway)
# Run whether user logged in: YES (S4U — no stored password; see principal note below)
# Retry:       NONE — abort-not-retry is chain policy (§6-A.3); a failed night is a
#              signal for Danni, not something to hammer at. (StartWhenAvailable still
#              covers "machine was off at 01:00".)
# Working dir: D:\verdmat-is\app
#
# The task runs scripts/nightly_delta_chain.sh via Git bash. Exit codes:
# 0 clean / 1 chain abort / 2 pre-flight refusal — readable in Task Scheduler
# as the last run result. Morning report: D:\verdmat-is\scraper_data\night_logs\.
#
# WU-pause dependency (§6-A.4-Q1): Windows Update pause expires after max 35 days;
# re-arm per the elevated-registry recipe before relying on long unattended stretches.

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-nightly-delta'
$bashExe   = 'C:\Program Files\Git\bin\bash.exe'
$chainSh   = 'D:\verdmat-is\app\scripts\nightly_delta_chain.sh'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $bashExe)) {
    throw "Git bash missing: $bashExe"
}
if (-not (Test-Path $chainSh)) {
    throw "Chain script missing: $chainSh"
}

# Build task pieces. bash -lc so the chain gets a login-ish environment (python on PATH).
$action = New-ScheduledTaskAction `
    -Execute $bashExe `
    -Argument '-lc "/d/verdmat-is/app/scripts/nightly_delta_chain.sh"' `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Daily -At '01:00'

# Wake from sleep; NO RestartCount (abort-not-retry); 8h limit covers the
# worst-case capped night (4 x 100 pages x 120s ~ 13h is impossible because the
# budget gate refuses any night that could exceed ~900 pages; a typical delta
# night is minutes) while still killing a wedged run before the 03:00+ backup
# day cycle repeats.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 8)

# Run whether user logged in or not — S4U principal, DELIBERATE DEVIATION from the
# backup-task pattern: the Password-logon principal NEVER prompts when passed via
# -Principal (prompting only happens with -User/-Password parameters), so registration
# failed with "user name or password is incorrect" and no stored credential
# (2026-06-12 elevated run). S4U needs no password, runs whether the user is logged in
# or not, and is sufficient for the chain: local disk + outbound HTTPS only, no
# network-share credentials needed. RunLevel Limited — delta needs no elevation.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

# If task already exists, replace it idempotently.
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    "Unregistered existing $taskName"
}

# Success echo is conditional: -ErrorAction Stop + try/catch so "Registered..." can
# NEVER print after a failed registration (the 2026-06-12 failure printed it anyway —
# misleading).
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description 'verdmat.is mbl nightly delta chain (4 modes, fetch-only v1, abort-not-retry). Daily 01:00 local. Exit 0 clean / 1 abort / 2 pre-flight refusal.' `
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
