# Register-ScheduledTask for verdmat-daily-lifecycle-sweep. Run once, from an
# ELEVATED PowerShell (admin), to install the scheduled task. Re-running is
# idempotent — it overwrites the existing definition.
#
# Schedule:    DAILY at 06:00 local (== GMT/UTC on this box). Clears the whole
#              01:00–05:00 pipeline window (delta 01:00, myigloo 02:00, sales 02:30,
#              backup 03:00, Sun cpi 04:00, Mon model-quality 05:00). The rent test
#              run at 06:40 confirmed the window is empty.
# Cadence:     The TRIGGER is daily; the weekly cadence lives in the state machine
#              (scripts/lifecycle_sweep_mbl.py --scheduled + scraper_data/lifecycle_sweep_state.json):
#                - rent : one full lota per week (~33 requests, ~33 min)
#                - sale : one full round per week, snapshotted at round start and
#                         RESUMED nightly over ~2 days under the §0.5 <1000/24h budget
#                         (700/24h sweep cap, backing off vs the delta chain's own
#                         trailing-24h page count). Most days nothing is due -> the run
#                         exits in seconds having made zero requests.
# Wake:        YES (wakes from sleep; AC sleep is disabled anyway).
# Run whether user logged in: YES (S4U — no stored password; Password-logon principals
#              fail registration silently via -Principal, see the delta-task note).
# Retry:       NONE — a failed night is a signal, and the state machine resumes the
#              sale round from its saved cursor on the next daily fire regardless.
# Time limit:  12h — covers the ~11.7h first sale night (700 req x 60s) with margin;
#              MultipleInstances IgnoreNew guards against any overlap into the next day.
# Working dir: D:\verdmat-is\app  (so `python -m scripts.lifecycle_sweep_mbl` resolves)
#
# WU DEPENDENCY (first sale night): the long sale night is exposed to Windows Update
# auto-restart. Resume-safety mitigates it (next fire continues from the cursor), but
# for the FIRST full sale round, pause Windows Update first (see the recipe presented
# alongside this script). Enable the first sale round deliberately, in the same elevated
# session, with:  python -m scripts.lifecycle_sweep_mbl --enable-sale

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-daily-lifecycle-sweep'
$pythonExe = 'C:\Python314\python.exe'
$scriptPy  = 'D:\verdmat-is\app\scripts\lifecycle_sweep_mbl.py'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $pythonExe)) {
    throw "python missing: $pythonExe"
}
if (-not (Test-Path $scriptPy)) {
    throw "Sweep script missing: $scriptPy"
}

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument '-m scripts.lifecycle_sweep_mbl --scheduled' `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Daily -At '06:00'

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 12)

# S4U principal — same locked pattern as verdmat-nightly-delta / -weekly-cpi-reanchor:
# a Password-logon principal NEVER prompts when passed via -Principal, so it fails
# registration with no stored credential. S4U needs no password and runs whether the
# user is logged in or not; the sweep needs local disk + outbound HTTPS (mbl GraphQL)
# + Supabase pooler over TLS only, no network-share credentials. RunLevel Limited.
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

# Conditional success echo: -ErrorAction Stop + try/catch so "Registered..." can NEVER
# print after a failed registration.
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description 'verdmat.is lifecycle sweep. Daily 06:00 GMT, state-gated: rent full weekly (~33 req), sale weekly round resumed nightly over ~2 days under the S0.5 <1000/24h budget (combined w/ the delta chain). Writes scraper.listing_lifecycle_events only. NOTE: the FIRST full sale round emits a ~8,900 confirmed_absent_1 wave (47.0% = 94/200 dry-run) — this is EXPECTED sticky-debt cleanup, NOT an alarm; the "active w/ last_seen>14d" health metric falls ~47%->~0 over 2 weeks and the first monitoring week should read the wave as a one-time baseline correction. Exit 0 clean / 1 error.' `
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
