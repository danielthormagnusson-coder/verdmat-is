# Register-ScheduledTask for verdmat-daily-sales-refresh. Run once, from an
# elevated PowerShell (admin), to install the scheduled task. Re-running is
# idempotent — it overwrites the existing definition.
#
# Schedule:    Daily at 02:30 local time. Machine TZ is Greenwich Standard Time
#              (Iceland = GMT year-round, so local == GMT). 02:30 clears the
#              01:00 mbl-delta task (different schema — scraper.*, no semantic-MV
#              REFRESH-lock collision even if it overlaps) and finishes well before
#              the 03:00 backup (loader REFRESH ~7 min -> done ~02:37).
# Wake:        YES (wakes from sleep; AC sleep is disabled anyway)
# Run whether user logged in: YES (S4U — no stored password; see principal note)
# Retry:       NONE — a failed day is a signal, not something to hammer.
#              StartWhenAvailable covers "machine was off at 02:30".
# Working dir: D:\verdmat-is\app
#
# The task runs scripts/daily_sales_refresh.py via the absolute python.exe. The
# loader fetches kaupskra itself in Step 0 — there is DELIBERATELY no separate
# refresh_kaupskra task (a sole-fetcher task would be an extra failure point; the
# md5 early-exit that made one tempting was removed in chunk 3). Exit codes:
# 0 clean (incl. NEW=0 no-op) / 1 fetch-or-upsert error — readable in Task
# Scheduler as the last run result. Run log: D:\daily_sales_refresh.log.

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-daily-sales-refresh'
$pythonExe = 'C:\Python314\python.exe'
$loaderPy  = 'D:\verdmat-is\app\scripts\daily_sales_refresh.py'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $pythonExe)) {
    throw "python missing: $pythonExe"
}
if (-not (Test-Path $loaderPy)) {
    throw "Loader script missing: $loaderPy"
}

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $loaderPy `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Daily -At '02:30'

# Wake from sleep; NO RestartCount (abort-not-retry); 1h limit kills a wedged run
# (a normal day is ~7 min: fetch no-op + derive + small upsert + 13 MV refresh).
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# S4U principal — same locked pattern as verdmat-nightly-delta: the Password-logon
# principal NEVER prompts when passed via -Principal (prompting only happens with
# -User/-Password), so a Password principal fails registration with no stored
# credential. S4U needs no password, runs whether the user is logged in or not, and
# is sufficient here: local disk + outbound HTTPS (HMS fetch) + Supabase pooler over
# TLS, no network-share credentials. RunLevel Limited — the loader needs no elevation.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Limited

# Idempotent replace.
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    "Unregistered existing $taskName"
}

# Conditional success echo: -ErrorAction Stop + try/catch so "Registered..." can
# NEVER print after a failed registration.
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description 'verdmat.is daily kaupskra fresh-data path: refresh_kaupskra -> derive -> upsert new sales (ON CONFLICT DO NOTHING) -> REFRESH 13 semantic MV. Daily 02:30 GMT. Decoupled from run_monthly. Exit 0 clean / 1 error.' `
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
