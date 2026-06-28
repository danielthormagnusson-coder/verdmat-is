<#
  arm_wu_nightly_guard.ps1 — Leið B WU night-window guard (DECISIONS 2026-06-28).

  PROBLEM: the active WU pause (HKLM UX Settings, until 2026-07-11) covers quality/
  feature updates but NOT servicing/Defender activity, which still runs daily. On the
  night of 27→28 Jun that background WU activity (01:53–01:55) coincided with — and
  disrupted — the long-running mbl delta chain (verdmat-nightly-delta, 01:00→~03:30),
  killing it between delta-sale and delta-rent (no clean abort line; promote/extraction
  never ran → mbl stale). The short myigloo task (02:00–02:19) slipped through.

  FIX (Leið B — decoupled, NOT inside the chain): two independent elevated scheduled
  tasks that quiet WU only during the night window, kept SEPARATE from the fragile
  chain so WU is ALWAYS re-enabled even if the chain dies:
    * verdmat-wu-guard-stop   @00:55  -> Stop  wuauserv + UsoSvc
    * verdmat-wu-guard-start  @03:35  -> Start wuauserv + UsoSvc   (the safety net)

  Window 00:55→03:35 covers the delta chain (01:00→~03:30) + myigloo (02:00).
  STOP, not DISABLE: services may trigger-restart on demand; we only mute the window.
  This is ADDITIVE to the WU pause — it does not touch the pause.

  Tasks run as NT AUTHORITY\SYSTEM (RunLevel Highest): SYSTEM controls services
  reliably without a stored password. Re-running this script updates the tasks
  in place (Register-ScheduledTask -Force) — idempotent, no duplicates.

  USAGE (Danni, elevated):
    powershell -ExecutionPolicy Bypass -File D:\verdmat-is\app\scripts\arm_wu_nightly_guard.ps1
  The two registered tasks invoke this same script with -Action Stop / -Action Start.
#>
param(
  [ValidateSet('Arm', 'Stop', 'Start')]
  [string]$Action = 'Arm'
)

$ErrorActionPreference = 'Stop'
$ScriptPath = $MyInvocation.MyCommand.Path
$LogDir     = 'D:\verdmat-is\scraper_data\logs'
$LogFile    = Join-Path $LogDir 'wu_guard.log'
$Services   = @('wuauserv', 'UsoSvc')
$WantStart  = @{ 'wuauserv' = 'Manual'; 'UsoSvc' = 'Automatic' }  # restore correct StartupType on Start

function Write-Log([string]$msg) {
  $line = ('{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Action, $msg)
  Write-Host $line
  try {
    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
  } catch { }  # never let logging failure break service control
}

function Test-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
    [Security.Principal.WindowsBuiltinRole]::Administrator)
}

# ── stop/start one service, report success/failure (never throw) ──────────────
function Invoke-WuService([string]$name, [string]$mode) {
  try {
    if ($mode -eq 'Stop') {
      Stop-Service -Name $name -Force -ErrorAction Stop
    } else {
      # ensure it was not left Disabled, then start
      try { Set-Service -Name $name -StartupType $WantStart[$name] -ErrorAction Stop } catch { }
      Start-Service -Name $name -ErrorAction Stop
    }
    Start-Sleep -Milliseconds 400
    $st = (Get-Service -Name $name).Status
    Write-Log ("{0} {1} OK -> {2}" -f $mode, $name, $st)
    return $true
  } catch {
    $st = try { (Get-Service -Name $name).Status } catch { 'unknown' }
    Write-Log ("{0} {1} FAILED ({2}) -> status={3}" -f $mode, $name, $_.Exception.Message, $st)
    return $false
  }
}

# ═══════════════════════════ Action: Stop / Start (task runtime) ══════════════
if ($Action -in @('Stop', 'Start')) {
  $ok = $true
  foreach ($s in $Services) { if (-not (Invoke-WuService $s $Action)) { $ok = $false } }
  Write-Log ("done (all_ok={0})" -f $ok)
  exit ($(if ($ok) { 0 } else { 1 }))
}

# ═══════════════════════════ Action: Arm (register tasks) ═════════════════════
if (-not (Test-Admin)) {
  Write-Host "REFUSE: must run elevated (Run as Administrator). Registering SYSTEM tasks + service control require admin." -ForegroundColor Red
  exit 2
}

Write-Host "=== Arming Leið B WU night-window guard ===" -ForegroundColor Cyan
Write-Host ("script: {0}" -f $ScriptPath)

$principal = New-ScheduledTaskPrincipal -UserId 'NT AUTHORITY\SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$psExe     = Join-Path $PSHOME 'powershell.exe'

function Register-Guard([string]$taskName, [string]$at, [string]$mode) {
  $action  = New-ScheduledTaskAction -Execute $psExe `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "{0}" -Action {1}' -f $ScriptPath, $mode)
  $trigger = New-ScheduledTaskTrigger -Daily -At $at
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
  $info = Get-ScheduledTask -TaskName $taskName
  Write-Host ("  registered {0,-24} @ {1}  ({2})  RunLevel={3} User={4}" -f `
    $taskName, $at, $mode, $info.Principal.RunLevel, $info.Principal.UserId) -ForegroundColor Green
}

Register-Guard 'verdmat-wu-guard-stop'  '00:55' 'Stop'
Register-Guard 'verdmat-wu-guard-start' '03:35' 'Start'

# ── PROBE: confirm this machine can actually stop/start the services (UsoSvc is
#    sometimes stubborn even for admin). Stop then Start each, report, leave running.
Write-Host ""
Write-Host "=== Probe (stop then start each service; leaves them running) ===" -ForegroundColor Cyan
$probe = @{}
foreach ($s in $Services) {
  $before = (Get-Service -Name $s).Status
  $stopOk = Invoke-WuService $s 'Stop'
  $startOk = Invoke-WuService $s 'Start'
  $after = (Get-Service -Name $s).Status
  $probe[$s] = [PSCustomObject]@{ Service = $s; Before = $before; StopOk = $stopOk; StartOk = $startOk; After = $after }
}
$probe.Values | Format-Table -AutoSize | Out-String -Width 120 | Write-Host

$allStop  = ($probe.Values | Where-Object { -not $_.StopOk }).Count -eq 0
$allStart = ($probe.Values | Where-Object { -not $_.StartOk }).Count -eq 0
Write-Host ""
if ($allStop -and $allStart) {
  Write-Host "RESULT: OK — both tasks registered, stop+start verified on both services. WU guard armed." -ForegroundColor Green
} elseif ($allStart) {
  Write-Host "RESULT: PARTIAL — tasks registered, START verified on both (WU always recoverable), but a STOP was refused (likely UsoSvc protected). The window will still mute whatever services do stop; report this line back." -ForegroundColor Yellow
} else {
  Write-Host "RESULT: ATTENTION — a START failed. Re-enable manually (Start-Service wuauserv,UsoSvc) and report the probe table." -ForegroundColor Red
}
Write-Host ("Log: {0}" -f $LogFile)
