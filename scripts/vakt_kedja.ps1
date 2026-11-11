# vakt_kedja.ps1 — cc268 (a)+(b): lokamerki næturkeðjunnar lesið úr night_YYYYMMDD.log (tillaga cc265, prófuð þar 13/13).
#
# Keðjan (nightly_delta_chain.sh) skrifar lokamerki í öllum endum sínum:
#   "=== CHAIN CLEAN (exit 0) ===" / "=== CHAIN DEGRADED:n (exit 0) ===" / "=== CHAIN FAIL (<þrep>, exit n) ==="
# og "promote: exit=0" um leið og scraper.listings er fersk (þaðan lesa öll biðverkin).
# Task Scheduler-staðan (State=Running) er EKKI lokamerki: mælt í cc265 að tímaþakið (atburður 329) drepur aðeins
# ræsinn og keðjan heldur áfram sem munaðarleysingi meðan verkið sýnir Ready (17.10: Ready 09:00, lauk 12:13).
#
# Tvær notkunir:
#   (1) Biðhlið (dot-source í cc193_keyra_verk.ps1):  . <slóð>\vakt_kedja.ps1 ; Get-KedjuStada
#       Biðverkið bíður meðan staðan er I_GANGI; heldur áfram á PROMOTE_LOKID / LOKID / FALL / ENGIN_RAESING.
#   (2) Vakt kl. 07:00 (eigið S4U-verk, cc268):  vakt_kedja.ps1 -Vakt [-Senda] [-Til <netfang>] [-Prof]
#       Sé keðja dagsins ekki LOKID: hávær lína í D:\verdmat_status.log (rás status-probe) og, með -Senda,
#       tölvupóstur um Resend. Lykill og sendandi eins og fable_worker.tilkynna_danna: RESEND_API_KEY úr
#       verdmat-ai\.env.local, svo D:\env.local; frá = ABENDING_FRA (staðfest lén); til = -Til eða
#       ABENDING_MOTTAKANDI. Lykill aldrei í logg.
#       -Prof: sendir póst með [PRÓF]-forskeyti hver sem staðan er (sannar rásina), skrifar EKKI í status-loggið.
#   rc: 0 = LOKID (eða próf sent), 2 = ólokið/fall, 4 = lykil/viðtakanda vantar, 5 = póstur féll.
#
#   cc299 — VIKULEGT LÍFSMARK (Danni 01.11.2026): á hreinni nótt sendir vaktin ekkert, svo þögn gat líka þýtt dauða
#       vakt. Með -Senda fer því einn póstur á MÁNUDAGSMORGNI hver sem staðan er: samantekt síðustu 7 nátta (lokamerki,
#       frestir, rc vaktar). Sé keðja dagsins ólokin á mánudegi fer EINN póstur (viðvörun + lífsmark). Berist enginn
#       mánudagspóstur er vaktin dauð. Varaleið: hafi ekkert lífsmark verið skráð í 7 daga (t.d. tölvan slökkt á mánudegi,
#       eða fyrsta keyrsla eftir uppsetningu) fer það í næstu keyrslu.
#       Hver -Vakt-keyrsla (ekki -Prof/-Thurrt) skrifar eina línu í $VaktLog: stöðu, frestslínur, rc og lífsmark.
#       Þaðan les samantektin rc vaktar; heitið er utan night_*.log-mynsturs status-probe.
#   -Lifsmark: þvingar lífsmarkið (hvaða dag sem er).  -Thurrt: prentar efni og meginmál, sendir EKKERT og skrifar
#       EKKERT (hvorki status-logg né $VaktLog). Lykill aldrei prentaður, aðeins hvort hann fannst.
param(
    [switch]$Vakt,
    [switch]$Senda,
    [switch]$Prof,
    [switch]$Lifsmark,
    [switch]$Thurrt,
    [string]$Til = '',
    [string]$NightLogs = 'D:\verdmat-is\scraper_data\night_logs',
    [string]$StatusFile = 'D:\verdmat_status.log',
    [string]$VaktLog = 'D:\verdmat-is\scraper_data\logs\kedjuvakt.log',
    [string]$EnvAi = 'D:\verdmat-is\verdmat-ai\.env.local',
    [string]$EnvRot = 'D:\env.local',
    [datetime]$Nu = (Get-Date)          # prófanir senda inn tíma; raunkeyrsla notar núið
)

function Get-KedjuStada {
    param([string]$Log = (Join-Path $NightLogs ('night_' + $Nu.ToString('yyyyMMdd') + '.log')),
          [datetime]$Til = $Nu)
    # Les aðeins línur með tímastimpli <= $Til (svo próf á gömlum loggum hermi stöðuna á þeim tíma).
    if (-not (Test-Path $Log)) { return 'ENGIN_RAESING' }
    $linur = Get-Content -Encoding utf8 $Log | Where-Object {
        $_ -match '^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) ' -and [datetime]::ParseExact($Matches[1], 'yyyy-MM-dd HH:mm:ss', $null) -le $Til }
    if (-not ($linur | Where-Object { $_ -like '*nightly delta chain start*' })) { return 'ENGIN_RAESING' }
    if ($linur | Where-Object { $_ -match '=== CHAIN FAIL' })                          { return 'FALL' }
    if ($linur | Where-Object { $_ -match '=== CHAIN (CLEAN|DEGRADED:\d+) \(exit 0\) ===' }) { return 'LOKID' }
    if ($linur | Where-Object { $_ -match ' promote: exit=0 ' })                       { return 'PROMOTE_LOKID' }
    return 'I_GANGI'
}

function Get-EnvGildi([string]$skra, [string]$lykill) {
    if (-not (Test-Path $skra)) { return '' }
    $l = Get-Content -Encoding utf8 $skra | Where-Object { $_ -like "$lykill=*" } | Select-Object -First 1
    if (-not $l) { return '' }
    return ($l.Substring($lykill.Length + 1).Trim()).Trim('"').Trim("'")
}

if (-not $Vakt) { return }   # dot-source / biðhlið: aðeins föllin

$Utf8 = New-Object System.Text.UTF8Encoding($false)
$nightLog = Join-Path $NightLogs ('night_' + $Nu.ToString('yyyyMMdd') + '.log')
$stada = Get-KedjuStada
$utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$frestad = @()
if (Test-Path $nightLog) { $frestad = @(Get-Content -Encoding utf8 $nightLog | Where-Object { $_ -match ' (FRESTAÐ|FRESTUR): ' }) }

$texti = "delta-keðja dagsins ($($Nu.ToString('dd.MM'))) kl. $($Nu.ToString('HH:mm')): staða $stada"
if ($frestad.Count) { $texti += " ($($frestad.Count) frestslínur)" }

# ── cc299: saga vaktar ($VaktLog) og hvort lífsmark fer í þessari keyrslu ──
# Línusnið: <utc> VAKT dags=yyyyMMdd kl=HH:mm stada=<staða> frest=<n> rc=<rc> lifsmark=<nei|sent:<id>|fell|vantar>
$saga = @()
if (Test-Path $VaktLog) { $saga = @(Get-Content -Encoding utf8 $VaktLog | Where-Object { $_ -match '^\S+Z VAKT dags=\d{8} ' }) }
$sidastaLifsmark = $null
foreach ($l in $saga) {
    if ($l -match ' dags=(\d{8}) .* lifsmark=sent') {
        $dl = [datetime]::ParseExact($Matches[1], 'yyyyMMdd', $null)
        if (-not $sidastaLifsmark -or $dl -gt $sidastaLifsmark) { $sidastaLifsmark = $dl }
    }
}
$lifsmarkNu = $false
if ($Lifsmark) { $lifsmarkNu = $true }
elseif (($Senda -or $Thurrt) -and -not $Prof) {
    if (-not $sidastaLifsmark) { $lifsmarkNu = $true }                                    # aldrei skráð (fyrsta keyrsla)
    elseif (($Nu.Date - $sidastaLifsmark).TotalDays -ge 7) { $lifsmarkNu = $true }        # varaleið: vika án lífsmarks
    elseif ($Nu.DayOfWeek -eq [DayOfWeek]::Monday -and $sidastaLifsmark -lt $Nu.Date) { $lifsmarkNu = $true }
}

function Get-Vikusamantekt {
    $dagar = @('sun', 'mán', 'þri', 'mið', 'fim', 'fös', 'lau')
    $radir = @(); $lokid = 0; $degr = 0; $frestSamtals = 0; $vaktSkrad = 0
    for ($i = 6; $i -ge 0; $i--) {
        $d = $Nu.Date.AddDays(-$i)
        $log = Join-Path $NightLogs ('night_' + $d.ToString('yyyyMMdd') + '.log')
        $tilD = $(if ($i -eq 0) { $Nu } else { $d.AddDays(1).AddSeconds(-1) })
        $st = Get-KedjuStada -Log $log -Til $tilD
        $merki = ''; $frest = ''; $nf = 0
        if (Test-Path $log) {
            $allt = @(Get-Content -Encoding utf8 $log)
            $c = $allt | Where-Object { $_ -match '^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d === CHAIN ' } | Select-Object -Last 1
            if ($c -and $c -match '^\d{4}-\d\d-\d\d (\d\d:\d\d):\d\d === (CHAIN .+?) ===') { $merki = "$($Matches[2]) kl. $($Matches[1])" }
            if ($merki -like 'CHAIN DEGRADED*') { $degr++ }
            $f = $allt | Where-Object { $_ -match 'FRESTUR-SAMANTEKT: ' } | Select-Object -Last 1
            if ($f -and $f -match 'FRESTUR-SAMANTEKT: (.+?) —') { $frest = 'frestur: ' + $Matches[1] }
            $nf = @($allt | Where-Object { $_ -match ' (FRESTAÐ|FRESTUR): ' }).Count
        }
        $frestSamtals += $nf
        if ($st -eq 'LOKID') { $lokid++ }
        $vr = '—'
        if ($i -eq 0) { $vr = 'þessi keyrsla' }
        else {
            $v = $saga | Where-Object { $_ -match " dags=$($d.ToString('yyyyMMdd')) " } | Select-Object -Last 1
            if ($v -and $v -match ' kl=(\S+) .* rc=(\d+)') { $vr = "rc $($Matches[2]) kl. $($Matches[1])"; $vaktSkrad++ }
        }
        if (-not $merki) { $merki = $(if (Test-Path $log) { 'ekkert lokamerki' } else { 'enginn næturlogg' }) }
        $radir += ('{0} {1}  {2,-13} {3,-30} {4,-30} vakt: {5}' -f $dagar[[int]$d.DayOfWeek], $d.ToString('dd.MM'), $st, $merki, $frest, $vr)
    }
    $haus = "Síðustu 7 nætur: lokið $lokid/7 (þar af DEGRADED $degr), frestslínur samtals $frestSamtals, vakt skráð $vaktSkrad/6 fyrri daga."
    if (-not $saga.Count) { $haus += ' (Vaktarsaga hefst með þessari keyrslu, svo rc fyrri daga vantar.)' }
    [pscustomobject]@{ Haus = $haus; Radir = $radir; Lokid = $lokid }
}

if (-not $Prof -and -not $Thurrt) {
    if ($stada -eq 'LOKID') { Write-Output "$utc delta-vakt OK: $texti" }
    else {
        [IO.File]::AppendAllText($StatusFile, "$utc !! VAKT-VIDVORUN: $texti — ÓLOKIÐ`r`n", $Utf8)
        Write-Output "$utc !! $texti — ÓLOKIÐ"
    }
}
$rc = $(if ($stada -eq 'LOKID') { 0 } else { 2 })
$lifsmarkStada = 'nei'
# cc324: sópunarvakt. Sópunin fellur ekki á rc: kort-lotan stóð í 15+ daga með rc 0. Les aðeins; ekkert í status-logg.
# rc 1 = FALL, 3 = mæling mistókst; hvort tveggja fer í póst. Breytir ekki rc keðjunnar (biðhliðin lesa hann).
$sopun = @(); $sopunRc = 0
# cc320 (11.11): -Prof keyrir líka sópunarvaktina (aðeins lestur), svo prófpósturinn sanni K0–K5-línurnar og UTF-8-lesturinn.
if ($true) {
    # cc320 (11.11): úttak Python er lesið sem UTF-8 í báða enda. Undir Task Scheduler er [Console]::OutputEncoding
    # OEM-síða (850/437) og „á" í K0–K5 kom út sem „├í" í pósti. Python skrifar UTF-8 (PYTHONUTF8), PowerShell les UTF-8.
    $fyrriKodun = [Console]::OutputEncoding; $fyrriPyUtf8 = $env:PYTHONUTF8
    try {
        $env:PYTHONUTF8 = '1'
        [Console]::OutputEncoding = $Utf8
        $sopun = @(& 'C:\Python314\python.exe' (Join-Path $PSScriptRoot 'sopunarvakt.py') 2>&1 | ForEach-Object { "$_" })
        $sopunRc = $LASTEXITCODE
    } catch { $sopun = @('SOPUNARVAKT: MÆLING MISTÓKST (ræsing)'); $sopunRc = 3 }
    finally {
        [Console]::OutputEncoding = $fyrriKodun
        if ($null -eq $fyrriPyUtf8) { Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue } else { $env:PYTHONUTF8 = $fyrriPyUtf8 }
    }
}
$postur = $Prof -or $lifsmarkNu -or (($Senda -or $Thurrt) -and ($stada -ne 'LOKID' -or $sopunRc -ne 0))

function Skra-Vakt([int]$r) {
    if ($Prof -or $Thurrt) { return }
    $lina = "$utc VAKT dags=$($Nu.ToString('yyyyMMdd')) kl=$($Nu.ToString('HH:mm')) stada=$stada frest=$($frestad.Count) rc=$r lifsmark=$lifsmarkStada sopun=$sopunRc"
    try {
        $m = Split-Path -Parent $VaktLog
        if ($m -and -not (Test-Path $m)) { New-Item -ItemType Directory -Force $m | Out-Null }
        [IO.File]::AppendAllText($VaktLog, $lina + "`r`n", $Utf8)
    } catch { Write-Output ('vaktarlogg féll: ' + $_.Exception.Message) }
}

if (-not $postur) { Skra-Vakt $rc; exit $rc }

$lykill = Get-EnvGildi $EnvAi 'RESEND_API_KEY'
if (-not $lykill) { $lykill = Get-EnvGildi $EnvRot 'RESEND_API_KEY' }
if (-not $Til) { $Til = Get-EnvGildi $EnvAi 'ABENDING_MOTTAKANDI' }
$fra = Get-EnvGildi $EnvAi 'ABENDING_FRA'
if (-not $fra) { $fra = 'verdmat.ai <onboarding@resend.dev>' }
# cc320 (11.11): sendandanafn er „verdmat.ai" í öllum pósti; ABENDING_FRA gefur aðeins netfangið (staðfest lén).
if ($fra -match '<([^<>\s]+@[^<>\s]+)>') { $fra = 'verdmat.ai <' + $Matches[1] + '>' } elseif ($fra -match '^\s*([^<>\s]+@[^<>\s]+)\s*$') { $fra = 'verdmat.ai <' + $Matches[1] + '>' }

$vika = $null
if ($lifsmarkNu) { $vika = Get-Vikusamantekt }
if ($Prof) { $efni = "[PRÓF] verdmat-vakt: $texti" + $(if ($lifsmarkNu) { ' + lífsmark' } else { '' }) }
elseif ($stada -ne 'LOKID') { $efni = "verdmat-vakt: $texti — ÓLOKIÐ" + $(if ($lifsmarkNu) { ' · vikulegt lífsmark' } else { '' }) }
elseif ($sopunRc -ne 0) { $efni = "verdmat-vakt: SÓPUN svelt eða ómæld — $($sopun[-1])" + $(if ($lifsmarkNu) { ' · vikulegt lífsmark' } else { '' }) }
else { $efni = "verdmat-vakt lífsmark: $($vika.Lokid)/7 nætur lokið — vika til $($Nu.ToString('dd.MM'))" }

$meginmal = "$texti`n"
if ($sopun.Count) { $meginmal += "`nSópun (cc324):`n" + ($sopun -join "`n") + "`n" }
if ($lifsmarkNu) {
    $meginmal += "`nVikulegt lífsmark vaktarinnar (cc299). Þessi póstur kemur á mánudagsmorgni hver sem staðan er;`n" +
        "berist hann ekki er vaktin (verdmat-daily-kedjuvakt) dauð eða pósturinn bilaður.`n`n" +
        $vika.Haus + "`n" + ($vika.Radir -join "`n") + "`n"
}
if ($Prof -or $stada -ne 'LOKID') {
    $hali = (Get-Content -Encoding utf8 $nightLog -Tail 8 -ErrorAction SilentlyContinue) -join "`n"
    $meginmal += "`nSíðustu línur $nightLog`:`n$hali`n"
    if ($frestad.Count) { $meginmal += "`nFrestslínur:`n" + ($frestad -join "`n") + "`n" }
}
if ($Prof) { $meginmal = "Prófsending vaktarinnar (cc268) — ekkert er að nema annað sjáist hér að neðan.`n`n" + $meginmal }

if ($Thurrt) {
    Write-Output ("ÞURRT — ekkert sent, ekkert skrifað. staða={0} lífsmark={1} (síðasta skráða: {2})" -f $stada, $lifsmarkNu, $(if ($sidastaLifsmark) { $sidastaLifsmark.ToString('dd.MM') } else { 'ekkert' }))
    Write-Output ("lykill fannst: {0}; viðtakandi fannst: {1}; frá: {2}" -f [bool]$lykill, [bool]$Til, $fra)
    Write-Output "Efni: $efni"; Write-Output '---'; Write-Output $meginmal
    exit 0
}
if (-not $lykill -or -not $Til) {
    Write-Output 'póstur: RESEND_API_KEY eða viðtakanda vantar'
    if ($lifsmarkNu) { $lifsmarkStada = 'vantar' }
    Skra-Vakt 4; exit 4
}
$body = @{ from = $fra; to = @($Til); subject = $efni; text = $meginmal } | ConvertTo-Json
try {
    $svar = Invoke-RestMethod -Method Post -Uri 'https://api.resend.com/emails' -Headers @{ Authorization = "Bearer $lykill" } `
        -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 30
    Write-Output ('póstur sendur, id=' + $svar.id)
    if ($lifsmarkNu) { $lifsmarkStada = 'sent:' + $svar.id }
} catch {
    Write-Output ('póstur féll: ' + $_.Exception.Message)
    if ($lifsmarkNu) { $lifsmarkStada = 'fell' }
    Skra-Vakt 5; exit 5
}
if ($Prof) { exit 0 }
Skra-Vakt $rc
exit $rc
