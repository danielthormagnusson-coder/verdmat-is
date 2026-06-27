# Register-ScheduledTask for verdmat-nightly-myigloo. Run once, from an elevated
# PowerShell (admin), to install the scheduled task. Re-running is idempotent — it
# overwrites the existing definition.
#
# DO NOT RUN until the guarded manual chain run has been verified (both layers update,
# active-set diff correct, keyless) — same gate discipline as the mbl delta task.
#
# Schedule:    Daily at 02:00 local time — clears the mbl delta window (01:00, normally
#              minutes) AND the 03:00 backup window. myigloo is a friendly CloudFront API;
#              a full sweep is ~15-22 min, so 02:00 leaves a clean hour either side and the
#              myigloo Supabase writes (source='myigloo' rows only) never race the mbl chain.
# Wake:        YES (wakes from sleep to run; AC sleep is disabled anyway)
# Run whether user logged in: YES (S4U — no stored password; Password-principal prompts and
#              fails silently, the 2026-06-12 mbl-task lesson)
# Retry:       NONE — abort-not-retry is chain policy; a failed night is a signal for Danni.
#              StartWhenAvailable still covers "machine was off at 02:00".
# Working dir: D:\verdmat-is\app
#
# Runs scripts/myigloo_nightly_chain.sh via Git bash. Exit codes: 0 clean / 1 chain abort /
# 2 pre-flight refusal — readable in Task Scheduler as the last run result. Morning report:
# D:\verdmat-is\scraper_data\night_logs\myigloo_night_YYYYMMDD.log.
#
# Keyless: no step calls an LLM, so ANTHROPIC_API_KEY is not needed in the task environment.

$ErrorActionPreference = 'Stop'

$taskName = 'verdmat-nightly-myigloo'
$bashExe  = 'C:\Program Files\Git\bin\bash.exe'
$chainSh  = 'D:\verdmat-is\app\scripts\myigloo_nightly_chain.sh'
$workDir  = 'D:\verdmat-is\app'

if (-not (Test-Path $bashExe)) { throw "Git bash missing: $bashExe" }
if (-not (Test-Path $chainSh)) { throw "Chain script missing: $chainSh" }

# bash -lc so the chain gets a login-ish environment (python on PATH).
$action = New-ScheduledTaskAction `
    -Execute $bashExe `
    -Argument '-lc "/d/verdmat-is/app/scripts/myigloo_nightly_chain.sh"' `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Daily -At '02:00'

# Wake from sleep; NO RestartCount (abort-not-retry). 2h limit comfortably covers the
# ~25-min chain (fetch ~22m + parse + canonical ~3m + lag1) while still killing a wedged
# run well before the 03:00 backup cycle.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# S4U principal — no password, runs whether the user is logged in or not. Sufficient for the
# chain: local disk + outbound HTTPS only, no network-share credentials. RunLevel Limited.
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
        -Description 'verdmat.is myigloo nightly full-sweep chain (fetch -> parse -> promote canonical + Layer 1 w/ active-set diff, abort-not-retry). Daily 02:00 local. Exit 0 clean / 1 abort / 2 pre-flight refusal.' `
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
