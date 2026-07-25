# Task Scheduler entry point for verdmat-nightly-backup. Registered by Step 1F.
# Runs the Python backup driver, captures stdout+stderr into a daily wrapper log,
# and exits with the driver's real exit code.
#
# cc43 (2026-07-25) — why this is no longer a `| Tee-Object` pipeline.
# The previous version was:
#     $ErrorActionPreference = 'Stop'
#     & python ...\backup_nightly.py *>&1 | Tee-Object -FilePath $wrapperLog
#     exit $LASTEXITCODE
# It lied in both directions, and 19 / 23 / 24 July are the evidence: a complete
# rclone log, a complete manifest with entries_ok=10, and NO _wrapper.log at all,
# with Task Scheduler reporting 0x80070001. Two defects compounded:
#   1. `*>&1` turns every native-stderr line into an ErrorRecord. Under
#      $ErrorActionPreference='Stop' the FIRST one is a TERMINATING error, so the
#      pipeline dies and `exit $LASTEXITCODE` is never reached — powershell.exe
#      exits 1 even though python exited 0. Reproduced: child exits 0 + one stderr
#      line => wrapper exit 1.
#   2. Python stdout is block-buffered when piped, and the driver's whole log is
#      ~1.3 KB — under the buffer. Nothing reaches Tee-Object until python exits.
#      So a stderr line arriving before that flush kills the pipeline before
#      Tee-Object ever creates the file. Reproduced: log file absent, exit 1.
# The result was a backup that verified itself only on the nights it had nothing
# to report. What actually wrote to stderr on those three nights is unrecoverable
# — the wrapper destroyed the only record of it. That is the defect being fixed.
#
# Now: streams are redirected at the OS level by Start-Process, which never routes
# through PowerShell's error machinery, so stderr cannot abort the run. The log is
# written from the captured files AFTER the driver exits, so it exists on every
# path — including a crash, a non-zero exit, or python not being found. The last
# line always states the real exit code, so the log and Task Scheduler's "Last Run
# Result" can no longer disagree.

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'   # driver output lands as it happens, not at process exit

$logDir = 'D:\verdmat-is\backup_log'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
$ts = Get-Date -Format 'yyyy-MM-ddTHH-mm'
$wrapperLog = Join-Path $logDir "$ts`_wrapper.log"
$outTmp = Join-Path $logDir "$ts`_wrapper.out.tmp"
$errTmp = Join-Path $logDir "$ts`_wrapper.err.tmp"

$started = Get-Date
$exitCode = 1
$launchError = $null

try {
    $py = (Get-Command python).Source
    $proc = Start-Process -FilePath $py `
                          -ArgumentList 'D:\verdmat-is\app\scripts\backup_nightly.py' `
                          -RedirectStandardOutput $outTmp `
                          -RedirectStandardError $errTmp `
                          -NoNewWindow -Wait -PassThru
    $exitCode = $proc.ExitCode
} catch {
    # Driver never started (python missing, D: locked, ...). Still gets a log.
    $exitCode = 1
    $launchError = $_.Exception.Message
}

$lines = New-Object System.Collections.Generic.List[string]
# -Encoding UTF8 is required: the driver writes UTF-8 (PYTHONIOENCODING) but
# Get-Content in PS 5.1 defaults to the system ANSI codepage, which turns every
# non-ASCII character in the log into mojibake.
if (Test-Path $outTmp) {
    $out = @(Get-Content -LiteralPath $outTmp -Encoding UTF8)
    if ($out.Count) { $lines.AddRange([string[]]$out) }
}
if (Test-Path $errTmp) {
    $err = @(Get-Content -LiteralPath $errTmp -Encoding UTF8)
    if ($err.Count) {
        $lines.Add('')
        $lines.Add('--- driver stderr ---')
        $lines.AddRange([string[]]$err)
    }
}
if ($launchError) {
    $lines.Add('')
    $lines.Add('--- wrapper failed to launch the driver ---')
    $lines.Add($launchError)
}

$elapsed = ((Get-Date) - $started).TotalSeconds
$lines.Add('')
$lines.Add(('=== wrapper: driver exit {0} after {1:n1}s, finished {2} ===' -f `
            $exitCode, $elapsed, (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK')))

Set-Content -LiteralPath $wrapperLog -Value $lines -Encoding UTF8
Remove-Item -LiteralPath $outTmp, $errTmp -Force -ErrorAction SilentlyContinue

exit $exitCode
