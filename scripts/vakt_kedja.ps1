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
param(
    [switch]$Vakt,
    [switch]$Senda,
    [switch]$Prof,
    [string]$Til = '',
    [string]$NightLogs = 'D:\verdmat-is\scraper_data\night_logs',
    [string]$StatusFile = 'D:\verdmat_status.log',
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

$EnvAi = 'D:\verdmat-is\verdmat-ai\.env.local'
$EnvRot = 'D:\env.local'
$Utf8 = New-Object System.Text.UTF8Encoding($false)
$nightLog = Join-Path $NightLogs ('night_' + $Nu.ToString('yyyyMMdd') + '.log')
$stada = Get-KedjuStada
$utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$frestad = @()
if (Test-Path $nightLog) { $frestad = @(Get-Content -Encoding utf8 $nightLog | Where-Object { $_ -match ' (FRESTAÐ|FRESTUR): ' }) }

$texti = "delta-keðja dagsins ($($Nu.ToString('dd.MM'))) kl. $($Nu.ToString('HH:mm')): staða $stada"
if ($frestad.Count) { $texti += " ($($frestad.Count) frestslínur)" }

if (-not $Prof) {
    if ($stada -eq 'LOKID') { Write-Output "$utc delta-vakt OK: $texti"; exit 0 }
    [IO.File]::AppendAllText($StatusFile, "$utc !! VAKT-VIDVORUN: $texti — ÓLOKIÐ`r`n", $Utf8)
    Write-Output "$utc !! $texti — ÓLOKIÐ"
}
if (-not ($Senda -or $Prof)) { exit 2 }

$lykill = Get-EnvGildi $EnvAi 'RESEND_API_KEY'
if (-not $lykill) { $lykill = Get-EnvGildi $EnvRot 'RESEND_API_KEY' }
if (-not $Til) { $Til = Get-EnvGildi $EnvAi 'ABENDING_MOTTAKANDI' }
$fra = Get-EnvGildi $EnvAi 'ABENDING_FRA'
if (-not $fra) { $fra = 'verdmat.ai <onboarding@resend.dev>' }
if (-not $lykill -or -not $Til) { Write-Output 'póstur: RESEND_API_KEY eða viðtakanda vantar'; exit 4 }

$efni = $(if ($Prof) { "[PRÓF] verdmat-vakt: $texti" } else { "verdmat-vakt: $texti — ÓLOKIÐ" })
$hali = (Get-Content -Encoding utf8 $nightLog -Tail 8 -ErrorAction SilentlyContinue) -join "`n"
$meginmal = "$texti`n`nSíðustu línur $nightLog`:`n$hali`n"
if ($frestad.Count) { $meginmal += "`nFrestslínur:`n" + ($frestad -join "`n") + "`n" }
if ($Prof) { $meginmal = "Prófsending vaktarinnar (cc268) — ekkert er að nema annað sjáist hér að neðan.`n`n" + $meginmal }
$body = @{ from = $fra; to = @($Til); subject = $efni; text = $meginmal } | ConvertTo-Json
try {
    $svar = Invoke-RestMethod -Method Post -Uri 'https://api.resend.com/emails' -Headers @{ Authorization = "Bearer $lykill" } `
        -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 30
    Write-Output ('póstur sendur, id=' + $svar.id)
} catch { Write-Output ('póstur féll: ' + $_.Exception.Message); exit 5 }
if ($Prof) { exit 0 }
exit 2
