# cc193_keyra_verk.ps1 — SAMEIGINLEGUR KEYRARI Task Scheduler-verkanna þriggja (cc193).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1 -Verk worker_poll
#   ... -Verk llt_refresh      ... -Verk verdvakt_refresh      (bættu -Thurrt við fyrir þurrpróf)
#
# HVAÐ HANN GERIR, í röð:
#   1. Logg: D:\verdmat-is\logs\<verk>.log — VIÐBÓT (aldrei yfirskrift), UTF-8 án BOM.
#      Stærðarvörn: fari skráin yfir 5 MB er hún færð í <verk>.log.1 (eldri .1 yfirskrifuð).
#   2. Umhverfi: D:\env.local (KEY=value, CRLF) hlaðið í PROCESS-umhverfið svo skriftur sem
#      lesa os.environ (cc188_verdvakt_refresh.py les ENDURNYJA_LYKILL ÞAÐAN — verdmat-ai er
#      ósnert á kóðahlið) sjái lyklana. Gildi eru ALDREI skrifuð í logg — aðeins fjöldi og
#      hvort ENDURNYJA_LYKILL er til.
#   3. Biðhlið (llt/verdvakt): sé verdmat-nightly-delta enn í keyrslu (State=Running) er beðið,
#      2 mín í senn, að hámarki 90 mín. Mælt 02.–07.09: keðjan lauk 02:40–04:55 (5 nætur),
#      en hún ber 8 klst þak, svo tímasetning ein er ekki hlið. Bíði hún lengur en hámarkið er
#      keyrt samt (bókað) — dagurinn fellur ekki á einni hægri nótt.
#   4. Keyrsla: C:\Python314\python.exe (full slóð, sannreynd 07.09: 3.14.3, psycopg2/pandas/
#      requests) úr vinnumöppu verksins; stdout+stderr í loggið; exit-kóði python verður
#      exit-kóði verksins (Last Run Result) — S4U-„success"-echo dugar ekki, lestu loggið.
#
# GIRÐINGAR WORKERSINS (standandi Fable-heimild, DECISIONS-tillaga cc193):
#   --leyfa-fable --hamark 3 --adeins-live  => (a) aðeins paid+live, (b) ≤3 Fable-köll per poll,
#   (c) kill-switch D:\verdmat-is\STOPP_FABLE (athugaður í workernum sjálfum, ekki hér),
#   (d) póstumferð/idempotens (email_sent_at) óbreytt.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('worker_poll', 'llt_refresh', 'verdvakt_refresh', 'myndahledsla')]
    [string]$Verk,
    [switch]$Thurrt
)

$ErrorActionPreference = 'Continue'
$Python = 'C:\Python314\python.exe'
$EnvRot = 'D:\env.local'
$LogDir = 'D:\verdmat-is\logs'
$LogMax = 5MB
$BidVerk = 'verdmat-nightly-delta'
$BidHamarkMin = 90

$Verkin = @{
    worker_poll = @{
        Skrift = 'D:\verdmat-is\app\scripts\fable_worker.py'
        Rok    = @('--once', '--leyfa-fable', '--hamark', '3', '--adeins-live')
        Thurr  = @('--once', '--dry-run', '--hamark', '3', '--adeins-live')
        WD     = 'D:\verdmat-is\app'
        Bida   = $false
    }
    llt_refresh = @{
        Skrift = 'D:\verdmat-is\app\scripts\cc180_llt_refresh.py'
        Rok    = @('--revalidate')
        Thurr  = @('--no-flip')
        WD     = 'D:\verdmat-is\app'
        Bida   = $true
    }
    verdvakt_refresh = @{
        Skrift = 'D:\verdmat-is\verdmat-ai\scripts\cc188_verdvakt_refresh.py'
        Rok    = @('--revalidate')
        Thurr  = @('--dry-run')
        WD     = 'D:\verdmat-is\verdmat-ai'
        Bida   = $true
    }
    # cc210: R2-manifest -> scraper.auglysingamyndir (cc117 þrep 4, áður aðeins handkeyrt 11.08).
    # Bíður myndasækisins (04:45), ekki næturkeðjunnar. Jöfnuður innbyggður í --skrifa (rc 2 = ROLLBACK).
    myndahledsla = @{
        Skrift  = 'D:\verdmat-is\app\scripts\hlada_auglysingamyndir.py'
        Rok     = @('--skrifa')
        Thurr   = @('--thurrkeyrsla')
        WD      = 'D:\verdmat-is\app'
        Bida    = $true
        BidVerk = 'verdmat-nightly-myndasaekjari'
    }
}
$V = $Verkin[$Verk]

# ── 1. logg ──────────────────────────────────────────────────────────────────
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Log = Join-Path $LogDir ($Verk + '.log')
$Utf8 = New-Object System.Text.UTF8Encoding($false)
function Skrifa([string]$s) {
    $lina = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' [keyrari] ' + $s
    [System.IO.File]::AppendAllText($Log, $lina + "`r`n", $Utf8)
}
if ((Test-Path $Log) -and ((Get-Item $Log).Length -gt $LogMax)) {
    Move-Item -Force $Log ($Log + '.1')
    Skrifa ('rotation: eldra logg fært í ' + $Log + '.1')
}

if ($Thurrt) { $rok = $V.Thurr } else { $rok = $V.Rok }
Skrifa ('=== START verk=' + $Verk + ' thurrt=' + [bool]$Thurrt + ' rok=' + ($rok -join ' ') + ' ===')

# ── 2. umhverfi úr D:\env.local (gildi ALDREI logguð) ───────────────────────
$nEnv = 0
if (Test-Path $EnvRot) {
    foreach ($l in (Get-Content $EnvRot -Encoding UTF8)) {
        $l = $l.Trim()
        if ($l.Length -eq 0 -or $l.StartsWith('#')) { continue }
        $i = $l.IndexOf('=')
        if ($i -lt 1) { continue }
        $k = $l.Substring(0, $i).Trim()
        $val = $l.Substring($i + 1).Trim()
        if ($k -match '^[A-Za-z_][A-Za-z0-9_]*$') {
            [Environment]::SetEnvironmentVariable($k, $val, 'Process')
            $nEnv++
        }
    }
}
$hefurLykil = -not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable('ENDURNYJA_LYKILL', 'Process'))
Skrifa ('env: ' + $nEnv + ' lyklar hlaðnir úr ' + $EnvRot + '; ENDURNYJA_LYKILL: ' + $(if ($hefurLykil) { 'til' } else { 'VANTAR' }))

# ── 3. biðhlið á næturkeðjuna ───────────────────────────────────────────────
if ($V.ContainsKey('BidVerk')) { $BidVerk = $V.BidVerk }   # cc210: biðhlið per verk
if ($V.Bida) {
    $t0 = Get-Date
    while ($true) {
        $st = $null
        try { $st = (Get-ScheduledTask -TaskName $BidVerk -ErrorAction Stop).State } catch { $st = 'ÓÞEKKT' }
        if ($st -ne 'Running') { break }
        $lidid = ((Get-Date) - $t0).TotalMinutes
        if ($lidid -ge $BidHamarkMin) {
            Skrifa ('biðhlið: ' + $BidVerk + ' enn Running eftir ' + [int]$lidid + ' mín — hámark náð, keyri samt')
            break
        }
        Skrifa ('biðhlið: ' + $BidVerk + ' er Running — bíð 2 mín (liðið ' + [int]$lidid + ' mín)')
        Start-Sleep -Seconds 120
    }
}

# ── 4. keyrsla ──────────────────────────────────────────────────────────────
if (-not (Test-Path $Python)) { Skrifa ('FALL: python vantar ' + $Python); exit 3 }
if (-not (Test-Path $V.Skrift)) { Skrifa ('FALL: skrifta vantar ' + $V.Skrift); exit 3 }
Set-Location $V.WD
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$linur = & $Python $V.Skrift @rok 2>&1 | ForEach-Object { [string]$_ }
$rc = $LASTEXITCODE
$sw.Stop()
if ($linur) { [System.IO.File]::AppendAllText($Log, (($linur -join "`r`n") + "`r`n"), $Utf8) }
Skrifa ('=== LOK verk=' + $Verk + ' rc=' + $rc + ' wall=' + [int]$sw.Elapsed.TotalSeconds + 's ===')
exit $rc
