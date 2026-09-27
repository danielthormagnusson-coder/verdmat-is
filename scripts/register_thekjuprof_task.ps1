# Register-ScheduledTask for verdmat-daily-thekjuprof (cc210 C1). Run from an ELEVATED
# PowerShell (admin) if S4U registration is refused. Re-running is idempotent.
#
# Schedule:    DAILY 07:15 local (== GMT/UTC on this box) — after the night chain (01:00,
#              ends 02:40–04:50) has promoted, so the delta cursor the probe reads is the
#              night's final one; before the 07:30 status probe.
# What:        scripts/thekjuprof_mbl.py — ~10 mbl requests at 120 s spacing (~18 min):
#              gap (exact aggregate w/ denominator), 4-page cluster sample, 32 "Á sölu"
#              ghost probes. Writes ONE row to scraper.thekjuprof + one line to
#              scraper_data/night_logs/night_YYYYMMDD.log; own log in scraper_data/logs/.
#              Runs alongside the 06:00 lifecycle sweep (also 120 s) -> combined ~60 s
#              spacing for ~18 min, = the fetch_mbl floor.
# Exit:        0 measured (also with VIÐVÖRUN) / 2 kill-switch / 3 error.
# Principal:   S4U, RunLevel Limited (locked pattern; Password principal fails silently).
# Python:      C:\Python314\python.exe — verified 27.09 (3.14.3, psycopg2 2.9.12, requests 2.33.1).

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-daily-thekjuprof'
$pythonExe = 'C:\Python314\python.exe'
$scriptPy  = 'D:\verdmat-is\app\scripts\thekjuprof_mbl.py'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $pythonExe)) { throw "python missing: $pythonExe" }
if (-not (Test-Path $scriptPy))  { throw "script missing: $scriptPy" }

$action = New-ScheduledTaskAction -Execute $pythonExe `
    -Argument 'scripts\thekjuprof_mbl.py' -WorkingDirectory $workDir
$trigger = New-ScheduledTaskTrigger -Daily -At '07:15'
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -WakeToRun -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    "Unregistered existing $taskName"
}
try {
    Register-ScheduledTask -TaskName $taskName `
        -Description 'verdmat.is cc210 C1 daglegt thekjuprof mbl: gap m/ nefnara, klasa-urtak, draugar a A solu-kortum. ~10 mbl-beidnir a 120 s. Skrifar scraper.thekjuprof + night-log. Exit 0 maelt / 2 kill-switch / 3 villa.' `
        -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
        -ErrorAction Stop | Out-Null
    "Registered $taskName"
    Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State
    "Next run time:"
    (Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime
}
catch {
    "REGISTRATION FAILED: $($_.Exception.Message)"
    exit 1
}
