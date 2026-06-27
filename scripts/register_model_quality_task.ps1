# Register-ScheduledTask for verdmat-weekly-model-quality. Run once, from an
# elevated PowerShell (admin), to install the scheduled task. Re-running is
# idempotent — it overwrites the existing definition.
#
# Schedule:    WEEKLY, Monday 05:00 local time. Machine TZ is Greenwich Standard
#              Time (Iceland = GMT year-round, so local == GMT). Monday 05:00 is a
#              CLEAN window with no overlap with any other verdmat job:
#                - mbl-delta            01:00 (daily)
#                - daily-sales-refresh  02:30 (daily, ~done 02:37)
#                - nightly-backup       03:00 (daily, ~done 03:30)
#                - cpi-reanchor         Sunday 04:00 (weekly)
#              Monday 05:00 is 25h after the cpi run and >1h after the daily/backup
#              chain finishes. The model-quality run is ~40 min (149 OOS Haiku calls
#              at ~13-16s each), so it lands entirely in open air.
# Cadence rationale: OOS quality is a slow weekly signal — new thinglyst OOS sales
#              accumulate daily, but a weekly snapshot is plenty. N is low (~149/week)
#              so the first weeks are noisy; the table ACCUMULATES rows per run
#              (metric_run_id), so trend reads out over time. A retracted listing
#              loses its söluyfirlit, so collecting weekly captures listings while live.
# Wake:        YES (wakes from sleep; AC sleep is disabled anyway).
# Run whether user logged in: YES (S4U — no stored password; see principal note).
# Retry:       NONE — a failed week is a signal, not something to hammer.
#              StartWhenAvailable covers "machine was off at 05:00 Monday".
# Working dir: D:\verdmat-is\app
#
# The task runs scripts/model_quality_eval.py with NO flags (full LIVE run):
#   EINKUNN 1 (baseline/all_oos)  — frozen iter4 predictions vs realized OOS prices.
#   EINKUNN 2 (full/paired_oos)   — same OOS properties, Haiku reads the söluyfirlit,
#                                   fills 108-field extraction, re-scores; GAP = full-baseline.
#   + selection check (baseline/all_oos vs baseline/paired_oos) → REPRESENTATIVE / SKEWED.
# Writes public.model_metrics (ON CONFLICT idempotent per metric_run_id) and logs to
# pipeline_runs/steps via migration_helpers. Exit 0 clean / 1 on write failure.
#
# API KEY: the Haiku half reads ANTHROPIC_API_KEY ONLY from D:\env.local (dotenv_values,
#          never os.environ) so the armed task bills the key WITHOUT exposing it to the
#          shell/CC environment. Extraction is cached at D:\model_quality_extraction_cache.jsonl
#          (keyed by fastnum+listing-hash) → unchanged listings are not re-paid week to week.
# Run log: D:\model_quality_eval.log (self-teed) + DB record in pipeline_runs/model_metrics.
#
# Estimated cost: ~$1/week at full N (less as the cache warms; only new/changed listings bill).

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-weekly-model-quality'
$pythonExe = 'C:\Python314\python.exe'
$scriptPy  = 'D:\verdmat-is\app\scripts\model_quality_eval.py'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $pythonExe)) {
    throw "python missing: $pythonExe"
}
if (-not (Test-Path $scriptPy)) {
    throw "model_quality_eval script missing: $scriptPy"
}

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $scriptPy `
    -WorkingDirectory $workDir

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '05:00'

# Wake from sleep; NO RestartCount (abort-not-retry); 2h limit kills a wedged run.
# Normal run ~40 min; each Haiku call is bounded to 60s (client timeout, no SDK retry)
# so a stuck call can no longer stall the run — 2h is generous headroom.
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# S4U principal — same locked pattern as verdmat-daily-sales-refresh /
# verdmat-weekly-cpi-reanchor: a Password-logon principal NEVER prompts when passed via
# -Principal, so it fails registration with no stored credential. S4U needs no password,
# runs whether the user is logged in or not, and is sufficient here: local disk + outbound
# HTTPS (Anthropic API) + Supabase pooler over TLS, no network-share credentials.
# RunLevel Limited — the eval needs no elevation.
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
        -Description 'verdmat.is weekly model-quality eval: two OOS scores on the same fresh out-of-sample sales (EINKUNN 1 = iter4 structured-only baseline vs realized; EINKUNN 2 = + Haiku söluyfirlit extraction; GAP = extraction contribution) + selection check. Writes public.model_metrics, logs pipeline_runs. Monday 05:00 GMT. Haiku key from D:\env.local only. Exit 0 clean / 1 error.' `
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
