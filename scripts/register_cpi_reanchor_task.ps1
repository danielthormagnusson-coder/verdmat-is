# Register-ScheduledTask for verdmat-weekly-cpi-reanchor. Run once, from an
# elevated PowerShell (admin), to install the scheduled task. Re-running is
# idempotent — it overwrites the existing definition.
#
# Schedule:    WEEKLY, Sunday 04:00 local time. Machine TZ is Greenwich Standard
#              Time (Iceland = GMT year-round, so local == GMT). 04:00 Sunday is a
#              clean window: mbl-delta 01:00, daily-sales 02:30 (~done 02:37),
#              backup 03:00 — all finished well before 04:00. The re-anchor + 13-MV
#              REFRESH took ~12-15s in dry-run, so the footprint is tiny.
# Cadence rationale: re-anchoring kaupverd_real is NOT day-sensitive (~0.1% real
#              difference per CPI month, e.g. 2026-07 -> 2026-08). Weekly is plenty
#              and means fewer runs; the DB-side gate no-ops every Sunday until a
#              new VNV month appears in cpi_verdtrygging.csv (expected 2026-08,
#              ~late July), then catches it automatically on the next Sunday.
# Wake:        YES (wakes from sleep; AC sleep is disabled anyway)
# Run whether user logged in: YES (S4U — no stored password; see principal note)
# Retry:       NONE — a failed week is a signal, not something to hammer.
#              StartWhenAvailable covers "machine was off at 04:00 Sunday".
# Working dir: D:\verdmat-is\app
#
# The task runs scripts/monthly_cpi_reanchor.py with NO flags (normal run): the
# DB-side gate (max(cpi_verdtrygging.csv) vs pipeline_config.sales_history_anchor_ym)
# no-ops until a new month arrives. On a real move it runs in ONE atomic txn
# (pre-flight snapshot -> real UPDATE + anchor + cpi_index) then REFRESH 13 MV.
# Exit 0 clean (incl. no-op) / 1 error. Run log: D:\monthly_cpi_reanchor.log.

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-weekly-cpi-reanchor'
$pythonExe = 'C:\Python314\python.exe'
$scriptPy  = 'D:\verdmat-is\app\scripts\monthly_cpi_reanchor.py'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $pythonExe)) {
    throw "python missing: $pythonExe"
}
if (-not (Test-Path $scriptPy)) {
    throw "Re-anchor script missing: $scriptPy"
}

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $scriptPy `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '04:00'

# Wake from sleep; NO RestartCount (abort-not-retry); 1h limit kills a wedged run
# (a normal run is ~15s: refresh_cpi + gate; on a real move ~12-15s UPDATE + 13 MV).
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# S4U principal — same locked pattern as verdmat-daily-sales-refresh /
# verdmat-nightly-delta: a Password-logon principal NEVER prompts when passed via
# -Principal, so it fails registration with no stored credential. S4U needs no
# password, runs whether the user is logged in or not, and is sufficient here:
# local disk + outbound HTTPS (Hagstofa fetch) + Supabase pooler over TLS, no
# network-share credentials. RunLevel Limited — the re-anchor needs no elevation.
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
        -Description 'verdmat.is weekly CPI re-anchor: refresh_cpi -> DB-side gate (no-op until new VNV month) -> on a real move, one atomic txn (pre-flight snapshot + re-anchor kaupverd_real + advance sales_history_anchor_ym + upsert cpi_index) -> REFRESH 13 semantic MV. Sunday 04:00 GMT. Exit 0 clean / 1 error.' `
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
