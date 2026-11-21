# LÍFTÍMASKILYRÐI (cc63 GO-bókun): cc65 fasi 1 (ops-vöktunarvélin) gleypir rökfræði
# próbans síðar og AFSKRÁIR hann berum orðum í fasa 3 — tvö kerfi lifa aldrei samhliða.
#
# verdmat_status_probe.ps1 — daily one-line health summary of every verdmat* scheduled
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
# cc337 (#5): undantekning — 267011 er hlutlaust á verki sem hefur EINGÖNGU LogonTrigger
# (t.d. cvakt-syna): það keyrir aðeins við innskráningu og „aldrei keyrt" er eðlilegt
# ástand, ekki bilun. Það hélt probe í varanlegu VAKT (79/99 dagar) og drekkti raunviðvörunum.
# Tímakveikt verk með 267011 er áfram hávært.
# cc337 (#5): verk eru valin með -like 'verdmat*', svo 'verdmat_*'-verkin (llt_refresh,
# worker_poll, verdvakt_refresh o.fl.) sjást líka; áður blind á þau (llt_refresh rc=2 í 17 d).
# Chain logs: newest night_*.log / myigloo_night_*.log. Þrjú stig (cc94):
#   CHAIN CLEAN (exit 0)      -> CLEAN
#   CHAIN DEGRADED:n (exit 0) -> DEGRADED(n) — keðjan kláraði, n köll féllu. FLAGG.
#   annað / vantar            -> ABORT
# and be from today or yesterday — older = STALE (chain not even starting).
#
# Usage:  powershell -File scripts\verdmat_status_probe.ps1 [-DryRun]
#   -DryRun: print the line(s) to stdout, write nothing.
# cc350: + réttindavakt (scripts/rettindavakt.py) — `rettindi=OK|FALL(n)|MAELING_MISTOKST` í línunni; annað en OK
#   er hávært og R-línurnar (á mannamáli) fylgja VAKT-VIDVORUN.

param([switch]$DryRun, [string]$RettindaSkra = '', [string]$SoluferliSkra = '')   # cc364: -SoluferliSkra = uttak soluferli_mv_stada.py ur skra (prof)   # cc350: -RettindaSkra = úttak réttindavaktar úr skrá (próf)

$ErrorActionPreference = 'Stop'
$statusFile = 'D:\verdmat_status.log'
$nightLogs  = 'D:\verdmat-is\scraper_data\night_logs'
$okResults  = @(0, 3)
$neutral    = @(267009)   # 0x41301 currently running

$offenders = @()

# ── scheduled tasks ──────────────────────────────────────────────────────────
$neverRan   = 267011       # 0x41303
$taskBits = foreach ($t in (Get-ScheduledTask | Where-Object TaskName -like 'verdmat*' |
                            Sort-Object TaskName)) {
    $info = $t | Get-ScheduledTaskInfo
    $rc = $info.LastTaskResult
    $short = $t.TaskName -replace '^verdmat-', ''
    $trig = @($t.Triggers)
    $adeinsInnskraning = $trig.Count -gt 0 -and
        -not ($trig | Where-Object { $_.CimClass.CimClassName -ne 'MSFT_TaskLogonTrigger' })
    $hlutlaust = ($neutral -contains $rc) -or (($rc -eq $neverRan) -and $adeinsInnskraning)
    if (($okResults -notcontains $rc) -and -not $hlutlaust) {
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

# ── cc350 (B1.3 cc347): réttindavakt — anon/authenticated mega aðeins lesa semantic.fasteignasala_* ×3 + PostGIS ──
# scripts/rettindavakt.py (aðeins lestur). FALL og mæling sem mistekst eru hávær; R-línurnar (mannamál) fara í
# status-loggið undir VAKT-VIDVORUN. Sama skrifta keyrir í vaktarpóstinum (vakt_kedja.ps1, 07:00).
$rettLinur = @()
$rettBit = 'rettindi=?'
if ($RettindaSkra) {
    $rettUt = @(Get-Content -Encoding utf8 $RettindaSkra)
    $rl = ($rettUt | Where-Object { $_ -like 'RETTINDAVAKT:*' } | Select-Object -Last 1)
    $rettRc = $(if ($rl -like 'RETTINDAVAKT: OK*') { 0 } elseif ($rl -like 'RETTINDAVAKT: FALL*') { 1 } else { 3 })
} else { try {
    $fyrriKodun = [Console]::OutputEncoding; $fyrriPyUtf8 = $env:PYTHONUTF8
    $env:PYTHONUTF8 = '1'
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $rettUt = @(& 'C:\Python314\python.exe' (Join-Path $PSScriptRoot 'rettindavakt.py') 2>&1 | ForEach-Object { "$_" })
    $rettRc = $LASTEXITCODE
} catch { $rettUt = @('RETTINDAVAKT: MAELING MISTOKST (raesing)'); $rettRc = 3 }
finally {
    [Console]::OutputEncoding = $fyrriKodun
    if ($null -eq $fyrriPyUtf8) { Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue } else { $env:PYTHONUTF8 = $fyrriPyUtf8 }
} }
$rettBit = switch ($rettRc) { 0 { 'rettindi=OK' } 1 { 'rettindi=FALL(' + @($rettUt | Where-Object { $_ -like 'R *' }).Count + ')' } default { 'rettindi=MAELING_MISTOKST' } }
if ($rettRc -ne 0) {
    $offenders += $rettBit
    $rettLinur = @($rettUt | Where-Object { $_ -like 'R *' -or $_ -like 'RETTINDAVAKT:*' })
}

# -- cc364: sidasta skref kedju/sopunar (endurnyjun scraper.soluferli_opin_mv), lesid ur pipeline_runs (adeins lestur).
#    Flokkun i EINU falli (scripts/soluferli_mv_stada.py): OK = graent, SLEPPT = hvorki villa ne graent (fyrra skref
#    feill og er havaert thar), VANTAR = hlutlaust (aldrei skrad), FALL og VANTAR48 (skrad adur, ekkert i 48 klst.) =
#    villa (offender). Bitinn: soluferli_mv=nott:X,sopun:Y.
$solUt = @()
if ($SoluferliSkra) { $solUt = @(Get-Content -Encoding utf8 $SoluferliSkra) } else { try {
    $fyrriKodun2 = [Console]::OutputEncoding; $fyrriPyUtf82 = $env:PYTHONUTF8
    $env:PYTHONUTF8 = '1'
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $solUt = @(& 'C:\Python314\python.exe' (Join-Path $PSScriptRoot 'soluferli_mv_stada.py') 2>&1 | ForEach-Object { "$_" })
} catch { $solUt = @('SOLUFERLI_MV: nott=MAELING_MISTOKST sopun=MAELING_MISTOKST') }
finally {
    [Console]::OutputEncoding = $fyrriKodun2
    if ($null -eq $fyrriPyUtf82) { Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue } else { $env:PYTHONUTF8 = $fyrriPyUtf82 }
} }
$sl = ($solUt | Where-Object { $_ -like 'SOLUFERLI_MV:*' } | Select-Object -Last 1)
$solBit = 'soluferli_mv=?'
if ($sl -match 'nott=(\S+) sopun=(\S+)') { $solBit = "soluferli_mv=nott:$($Matches[1]),sopun:$($Matches[2])" }
if ($solBit -match ':(FALL|VANTAR48)') { $offenders += $solBit }   # cc364 21.11: SLEPPT og VANTAR (aldrei skrad) eru hlutlaus

# ── one summary line (+ loud line on trouble) ────────────────────────────────
$utc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$flag = if ($offenders.Count) { 'VAKT' } else { 'OK  ' }
$lines = @("$utc $flag tasks[$($taskBits -join ' ')] $($chainBits -join ' ') $rettBit $solBit")
if ($offenders.Count) {
    $lines += "$utc !! VAKT-VIDVORUN: $($offenders -join ', ')"
    foreach ($r in $rettLinur) { $lines += "$utc !! $r" }
}

if ($DryRun) {
    "[dry-run] would append to ${statusFile}:"
    $lines
} else {
    $lines | Out-File -FilePath $statusFile -Append -Encoding utf8
    $lines
}
exit 0
