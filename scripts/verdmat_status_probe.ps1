# LÍFTÍMASKILYRÐI (cc63 GO-bókun): cc65 fasi 1 (ops-vöktunarvélin) gleypir rökfræði
# próbans síðar og AFSKRÁIR hann berum orðum í fasa 3 — tvö kerfi lifa aldrei samhliða.
#
# verdmat_status_probe.ps1 — daily one-line health summary of every verdmat-* scheduled
# task + the two nightly chain logs, appended to D:\verdmat_status.log. Third incident
# (extraction ImportError, 6 silent nights 27.07-01.08) that a reader of LastTaskResult
# would have caught on morning one — this is that reader. No mail; the file is the channel.
#
#   normal:  <utc> OK    tasks[...] delta=... myigloo=...
#   trouble: <utc> VAKT  tasks[...] delta=... myigloo=...
#            <utc> !! VAKT-VIDVORUN: <offender list>          (extra loud line)
#
# OK result codes per task: 0 (clean) and 3 (designed guard-abort: cpi-reanchor vordur,
# rent-restep guard). 267009 (0x41301 = still running) is neutral. EVERYTHING else is
# loud — incl. 1/2 (chain abort / preflight or domsregla-HALT) and 267011 (0x41303 =
# never ran; a registered task that never fires is a scheduler problem, not a no-op).
# Chain logs: newest night_*.log / myigloo_night_*.log. Þrjú stig (cc94):
#   CHAIN CLEAN (exit 0)      -> CLEAN
#   CHAIN DEGRADED:n (exit 0) -> DEGRADED(n) — keðjan kláraði, n köll féllu. FLAGG.
#   annað / vantar            -> ABORT
# and be from today or yesterday — older = STALE (chain not even starting).
#
# Usage:  powershell -File scripts\verdmat_status_probe.ps1 [-DryRun]
#   -DryRun: print the line(s) to stdout, write nothing.

param([switch]$DryRun)

$ErrorActionPreference = 'Stop'
$statusFile = 'D:\verdmat_status.log'
$nightLogs  = 'D:\verdmat-is\scraper_data\night_logs'
$okResults  = @(0, 3)
$neutral    = @(267009)   # 0x41301 currently running

$offenders = @()

# ── scheduled tasks ──────────────────────────────────────────────────────────
$taskBits = foreach ($t in (Get-ScheduledTask | Where-Object TaskName -like 'verdmat-*' |
                            Sort-Object TaskName)) {
    $info = $t | Get-ScheduledTaskInfo
    $rc = $info.LastTaskResult
    $short = $t.TaskName -replace '^verdmat-', ''
    if (($okResults -notcontains $rc) -and ($neutral -notcontains $rc)) {
        $offenders += ('{0}=0x{1:X}' -f $short, $rc)
    }
    '{0}=0x{1:X}' -f $short, $rc
}

# ── chain logs (newest per chain; CLEAN / ABORT / STALE / MISSING) ───────────
function Get-ChainVerdict([string]$pattern, [string]$label) {
    $log = Get-ChildItem (Join-Path $nightLogs $pattern) -ErrorAction SilentlyContinue |
           Sort-Object Name | Select-Object -Last 1
    if (-not $log) { $script:offenders += "$label=MISSING"; return "$label=MISSING" }
    $day = [datetime]::ParseExact(($log.BaseName -replace '.*_(\d{8})$', '$1'), 'yyyyMMdd', $null)
    # cc94 — DEGRADED prófað Á UNDAN CLEAN. Ástæða: sama loggskrá getur borið
    # báðar línurnar sé keðja endurkeyrð handvirkt sama dag (append-only
    # næturlogg), og þá á VERRA stigið að ráða — annars felur ein hrein
    # endurkeyrsla skerta nótt.
    $deg = Select-String -Path $log.FullName -Pattern 'CHAIN DEGRADED:(\d+) \(exit 0\)' |
           Select-Object -Last 1
    $verdict = if ($deg) { 'DEGRADED({0})' -f $deg.Matches[0].Groups[1].Value }
        elseif (Select-String -Path $log.FullName -Pattern 'CHAIN CLEAN \(exit 0\)' -Quiet) {
            'CLEAN' } else { 'ABORT' }
    if ($day -lt (Get-Date).Date.AddDays(-1)) { $verdict = "STALE($($log.BaseName))" }
    if ($verdict -ne 'CLEAN') { $script:offenders += "$label=$verdict" }
    '{0}={1}:{2}' -f $label, $day.ToString('MMdd'), $verdict
}
$chainBits = @(
    (Get-ChainVerdict 'night_*.log'         'delta'),
    (Get-ChainVerdict 'myigloo_night_*.log' 'myigloo')
)

# ── one summary line (+ loud line on trouble) ────────────────────────────────
$utc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$flag = if ($offenders.Count) { 'VAKT' } else { 'OK  ' }
$lines = @("$utc $flag tasks[$($taskBits -join ' ')] $($chainBits -join ' ')")
if ($offenders.Count) {
    $lines += "$utc !! VAKT-VIDVORUN: $($offenders -join ', ')"
}

if ($DryRun) {
    "[dry-run] would append to ${statusFile}:"
    $lines
} else {
    $lines | Out-File -FilePath $statusFile -Append -Encoding utf8
    $lines
}
exit 0
