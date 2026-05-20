# Task Scheduler entry point for verdmat-nightly-backup. Registered by Step 1F.
# Runs the Python backup driver with stdout/stderr captured into a daily log
# file. Exit code propagates so Task Scheduler "Last Run Result" reflects
# success/failure honestly.

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'

$logDir = 'D:\verdmat-is\backup_log'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$ts = Get-Date -Format 'yyyy-MM-ddTHH-mm'
$wrapperLog = Join-Path $logDir "$ts`_wrapper.log"

& python 'D:\verdmat-is\app\scripts\backup_nightly.py' *>&1 | Tee-Object -FilePath $wrapperLog
exit $LASTEXITCODE
