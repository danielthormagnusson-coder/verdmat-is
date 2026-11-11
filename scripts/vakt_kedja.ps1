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
#   cc337 (#5): DEGRADED-NÓTT SENDIR PÓST. Biðhliðin telja CHAIN DEGRADED:n sem LOKID (keðjan kláraði) og það
#       helst; en vaktin sendir nú póst (með -Senda) þegar lokamerki dagsins er DEGRADED:n (n köll féllu), því
#       39/151 nætur voru DEGRADED án nokkurs pósts (t.d. Haiku-inneign búin í ~30 nætur, exit 0). rc helst 0
#       (keðjan kláraði); vaktarlínan ber degr=<n>. Sé lokamerkið bæði CLEAN og DEGRADED (endurkeyrsla) ræður
#       VERRA stigið, eins og í status-probe (cc94).
#   cc337 (Danni/arkitekt 11.11) — PÓSTUR Á MANNAMÁLI: þrjú stig.
#       í lagi       → „verdmat.ai í lagi – ekkert að gera“ (fer aðeins sem vikulegt lífsmark)
#       að jafna sig → þekkt ástand sem lagast sjálft; framvinda og áætlaður lokadagur lesin ÚR GÖGNUNUM
#                      (lifecycle_sweep_runs.jsonl: rent_cursor/sale_cursor á móti heildinni, hraði = færsla
#                      milli tveggja síðustu keyrslna). Ekkert að gera.
#       þarf athygli → „verdmat.ai ÞARF ATHYGLI – <hvað>“ + tilbúinn texti til að líma í master.
#       Aðeins „þarf athygli“ notar orðið FALL. Tæknilínur (K0–K5, tímastimplar, frestslínur, lokamerki) standa
#       neðst undir „Fyrir lotur“, óbreyttar að efni (í „að jafna sig“ er K-merkið FALL ritað „á eftir“).
#   -SopunSkra <skrá>: les úttak sópunarvaktar úr skrá í stað þess að keyra hana (próf og sýnishorn).
#   -SopunKeyrslur <skrá>: lifecycle_sweep_runs.jsonl (framvinda yfirferðar).
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
    [datetime]$Nu = (Get-Date),         # prófanir senda inn tíma; raunkeyrsla notar núið
    [string]$SopunSkra = '',
    [string]$SopunKeyrslur = 'D:\verdmat-is\scraper_data\lifecycle_sweep_runs.jsonl'
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

# cc337: DEGRADED:n á lokamerki dagsins (aðeins línur <= $Nu, sama regla og Get-KedjuStada).
$degrN = 0
if ($stada -eq 'LOKID' -and (Test-Path $nightLog)) {
    $dl = Get-Content -Encoding utf8 $nightLog | Where-Object {
        $_ -match '^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) .*=== CHAIN DEGRADED:(\d+) \(exit 0\) ===' -and
        [datetime]::ParseExact($Matches[1], 'yyyy-MM-dd HH:mm:ss', $null) -le $Nu } | Select-Object -Last 1
    if ($dl -and $dl -match 'CHAIN DEGRADED:(\d+)') { $degrN = [int]$Matches[1] }
}
$texti = "delta-keðja dagsins ($($Nu.ToString('dd.MM'))) kl. $($Nu.ToString('HH:mm')): staða $stada"
if ($degrN -gt 0) { $texti += " — DEGRADED: $degrN köll féllu" }
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
    if ($stada -eq 'LOKID' -and $degrN -gt 0) { Write-Output "$utc delta-vakt DEGRADED: $texti" }
    elseif ($stada -eq 'LOKID') { Write-Output "$utc delta-vakt OK: $texti" }
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
if ($SopunSkra) {
    $sopun = @(Get-Content -Encoding utf8 $SopunSkra)
    $sl = ($sopun | Where-Object { $_ -match '^SOPUNARVAKT: ' } | Select-Object -Last 1)
    $sopunRc = $(if ($sl -match ': OK') { 0 } elseif ($sl -match 'MISTÓKST') { 3 } else { 1 })
}
else {
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
# ── cc337: stig á mannamáli ──────────────────────────────────────────────────────────────────────────
$athygli = @()   # hver: @{ Stutt = '<3–5 orð>'; Hvad = '...'; Thydir = '...'; Master = '...' }
$jafna = @()     # hver: @{ Stutt = '...'; Hvad = '...'; Thydir = '...' }
$dagur = $Nu.ToString('dd.MM')
switch ($stada) {
    'FALL' { $athygli += @{ Stutt = 'næturuppfærsla stöðvaðist'
        Hvad = 'Næturuppfærslan stöðvaðist áður en hún kláraðist.'
        Thydir = 'Nýjar auglýsingar og verðbreytingar frá því í gær vantar á vefinn. Vefurinn er uppi og sýnir eldri gögn.'
        Master = "verdmat-vakt $($dagur): næturkeðjan stöðvaðist (CHAIN FAIL). Finndu orsök í $nightLog, keyrðu keðjuna aftur ef það er öruggt og segðu mér hvað gerðist." } }
    'ENGIN_RAESING' { $athygli += @{ Stutt = 'næturuppfærsla fór ekki af stað'
        Hvad = 'Næturuppfærslan fór aldrei af stað í nótt.'
        Thydir = 'Engin ný gögn bættust við í nótt. Vefurinn er uppi og sýnir gögn frá því í gær.'
        Master = "verdmat-vakt $($dagur): næturkeðjan fór ekki af stað (enginn næturlogg eða ekkert upphafsmerki). Athugaðu verkið verdmat-nightly-delta og segðu mér hvað gerðist." } }
    'I_GANGI' { $athygli += @{ Stutt = 'næturuppfærsla enn í gangi'
        Hvad = "Næturuppfærslan var enn í gangi kl. $($Nu.ToString('HH:mm')) en á að vera búin."
        Thydir = 'Nýjustu gögn næturinnar eru ekki enn komin á vefinn.'
        Master = "verdmat-vakt $($dagur): næturkeðjan var enn í gangi kl. $($Nu.ToString('HH:mm')) (ekkert lokamerki). Athugaðu hvort hún hangir og segðu mér stöðuna." } }
    'PROMOTE_LOKID' { $athygli += @{ Stutt = 'næturuppfærsla kláraðist ekki'
        Hvad = "Nýjar auglýsingar komust inn í nótt, en seinni hluti uppfærslunnar var ekki búinn kl. $($Nu.ToString('HH:mm'))."
        Thydir = 'Auglýsingarnar eru nýjar, en greining og verðmat nýjustu auglýsinga geta vantað.'
        Master = "verdmat-vakt $($dagur): næturkeðjan náði promote en ekkert lokamerki kl. $($Nu.ToString('HH:mm')). Athugaðu seinni þrep keðjunnar og segðu mér stöðuna." } }
}
if ($degrN -gt 0) {
    $athygli += @{ Stutt = 'næturgreining mistókst að hluta'
        Hvad = "Næturuppfærslan kláraðist, en $degrN sjálfvirkar aðgerðir mistókust (oftast greining á texta auglýsinga)."
        Thydir = 'Vefurinn er uppi og auglýsingar eru nýjar, en hluta nýrra auglýsinga vantar greiningu (t.d. ástand eða eigindi úr lýsingu).'
        Master = "verdmat-vakt $($dagur): næturkeðjan endaði CHAIN DEGRADED:$degrN. Finndu hvað féll í $nightLog og leggðu til lagfæringu." }
}
# Sópun: K2/K3 (leigu-/söluyfirferð ekki lokið innan þaks) er „að jafna sig“ EF bendillinn færðist í síðustu keyrslu.
$sopunFoll = @($sopun | Where-Object { $_ -match '^(K\d) FALL' } | ForEach-Object { ($_ -split ' ')[0] })
$keyrslur = @()
if (Test-Path $SopunKeyrslur) {
    $keyrslur = @(Get-Content -Encoding utf8 $SopunKeyrslur | Where-Object { $_.Trim() } | Select-Object -Last 2 | ForEach-Object { $_ | ConvertFrom-Json })
}
function Tala([int]$n) { $n.ToString('N0', [Globalization.CultureInfo]::GetCultureInfo('is-IS')) }
function Get-Framvinda([string]$teg) {
    if ($keyrslur.Count -lt 2) { return $null }
    $a = $keyrslur[0]; $b = $keyrslur[1]
    $bendill = [int]$b."$($teg)_cursor"; $heild = [int]$b."$($teg)_total"; $fyrri = [int]$a."$($teg)_cursor"
    $faersla = $bendill - $fyrri
    if ($heild -le 0 -or $faersla -le 0) { return $null }
    $eftir = [math]::Max(0, $heild - $bendill)
    $keyrslurEftir = [math]::Ceiling($eftir / $faersla)
    $lok = ([datetime]$b.at).ToUniversalTime().Date.AddDays($keyrslurEftir)
    [pscustomobject]@{ Bendill = $bendill; Heild = $heild; Faersla = $faersla; Lok = $lok }
}
$heitiTeg = @{ K2 = @('rent', 'leiguauglýsinga', 'leiguyfirferð'); K3 = @('sale', 'söluauglýsinga', 'söluyfirferð') }
$jafnaK = @()
foreach ($k in $sopunFoll) {
    if ($heitiTeg.ContainsKey($k)) {
        $f = Get-Framvinda $heitiTeg[$k][0]
        $ht = $heitiTeg[$k]
        if ($f) {
            $jafnaK += $k
            $jafna += @{ Stutt = "$($ht[2]) klárast $($f.Lok.ToString('dd.MM'))"
                Hvad = ("Yfirferð {0} (athugað hvort þær séu enn í birtingu) er á eftir áætlun en gengur: {1} af {2} búnar, um {3} á dag. Áætlað að hún klárist {4}." -f $ht[1], (Tala $f.Bendill), (Tala $f.Heild), (Tala $f.Faersla), $f.Lok.ToString('dd.MM.yyyy'))
                Thydir = "Á meðan geta nokkrar $($ht[1].Replace('auglýsinga','auglýsingar')) sem eru farnar af auglýsingavefnum enn birst sem virkar. Annað á vefnum er óháð þessu." }
        } else {
            $athygli += @{ Stutt = "$($ht[2]) stopp"
                Hvad = "Yfirferð $($ht[1]) hefur ekki lokið hring innan tímamarka og bendillinn hreyfðist ekki í síðustu keyrslu."
                Thydir = "$($ht[1].Substring(0,1).ToUpper() + $ht[1].Substring(1).Replace('auglýsinga','auglýsingar')) sem eru farnar af markaði geta birst áfram sem virkar á verdmat.ai."
                Master = "verdmat-vakt $($dagur): sópunarvakt $k FALL og bendill $($ht[0])_cursor hreyfist ekki (lifecycle_sweep_runs.jsonl). Finndu hvers vegna yfirferðin stendur og leggðu til lagfæringu." }
        }
    }
}
$sopunAnnad = @($sopunFoll | Where-Object { $jafnaK -notcontains $_ -and -not $heitiTeg.ContainsKey($_) })
$sopunLysing = @{
    K0 = 'Yfirferð auglýsinga keyrði ekki síðasta sólarhring.'
    K1 = 'Yfirferðin hefur ekki skráð neina auglýsingu sem horfna eða selda í tvo sólarhringa.'
    K4 = 'Óvenju margar auglýsingar sem eru horfnar af auglýsingavefnum birtast enn sem virkar.'
    K5 = 'Yfirferðin sendi engar fyrirspurnir í tveimur keyrslum í röð, þótt verk biðu.'
}
if ($sopunAnnad.Count) {
    $athygli += @{ Stutt = 'yfirferð auglýsinga í ólagi'
        Hvad = (($sopunAnnad | ForEach-Object { $sopunLysing[$_] }) -join ' ')
        Thydir = 'Auglýsingar sem eru farnar af markaði geta birst áfram sem virkar á verdmat.ai.'
        Master = "verdmat-vakt $($dagur): sópunarvakt FALL ($($sopunAnnad -join ',')). Línurnar eru í póstinum undir Fyrir lotur. Finndu orsök og leggðu til lagfæringu." }
}
if ($sopunRc -eq 3) {
    $athygli += @{ Stutt = 'vaktin gat ekki mælt'
        Hvad = 'Vaktin gat ekki mælt yfirferð auglýsinga (tenging við gagnagrunn eða skrá vantaði).'
        Thydir = 'Óvíst hvort yfirferðin gengur; vefurinn sjálfur er ekki endilega fyrir áhrifum.'
        Master = "verdmat-vakt $($dagur): sópunarvakt MÆLING MISTÓKST (rc 3). Keyrðu scripts/sopunarvakt.py og segðu mér hvað brást." }
}
$stig = $(if ($athygli.Count) { 'athygli' } elseif ($jafna.Count) { 'jafna' } else { 'lagi' })

$postur = $Prof -or $lifsmarkNu -or (($Senda -or $Thurrt) -and $stig -ne 'lagi')

function Skra-Vakt([int]$r) {
    if ($Prof -or $Thurrt) { return }
    $lina = "$utc VAKT dags=$($Nu.ToString('yyyyMMdd')) kl=$($Nu.ToString('HH:mm')) stada=$stada frest=$($frestad.Count) rc=$r lifsmark=$lifsmarkStada sopun=$sopunRc degr=$degrN"
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
$efni = switch ($stig) {
    'athygli' { 'verdmat.ai ÞARF ATHYGLI – ' + $athygli[0].Stutt + $(if ($athygli.Count -gt 1) { ' o.fl.' } else { '' }) }
    'jafna'   { 'verdmat.ai að jafna sig – ekkert að gera (' + (($jafna | ForEach-Object { $_.Stutt }) -join ', ') + ')' }
    default   { 'verdmat.ai í lagi – ekkert að gera' }
}
if ($lifsmarkNu) { $efni += ' · vikuyfirlit' }
if ($Prof) { $efni = '[PRÓF] ' + $efni }

$m = @()
if ($Prof) { $m += 'PRÓF — sýnishorn af vaktarpósti. Ekkert þarf að gera vegna þessa pósts.'; $m += '' }
$m += switch ($stig) { 'athygli' { 'STAÐA: ÞARF ATHYGLI' } 'jafna' { 'STAÐA: AÐ JAFNA SIG (ekkert að gera)' } default { 'STAÐA: Í LAGI' } }
$m += ''
$m += 'Hvað gerðist:'
if ($stig -eq 'lagi') { $m += '- Næturuppfærslan gekk eðlilega og yfirferð auglýsinga er á áætlun.' }
foreach ($x in $athygli) { $m += '- ' + $x.Hvad }
foreach ($x in $jafna) { $m += '- ' + $x.Hvad }
if ($stig -ne 'lagi' -and $stada -eq 'LOKID' -and $degrN -eq 0) { $m += '- Næturuppfærslan sjálf gekk eðlilega.' }
$m += ''
$m += 'Hvað það þýðir fyrir vefinn:'
if ($stig -eq 'lagi') { $m += '- Vefurinn er uppi með gögn næturinnar. Ekkert vantar.' }
foreach ($x in $athygli) { $m += '- ' + $x.Thydir }
foreach ($x in $jafna) { $m += '- ' + $x.Thydir }
$m += ''
$m += 'Hvað þú þarft að gera:'
if ($stig -eq 'athygli') {
    $m += '- Límdu textann hér að neðan í master-lotuna:'
    $m += ''
    $m += '----------'
    foreach ($x in $athygli) { $m += $x.Master }
    $m += '----------'
} elseif ($stig -eq 'jafna') {
    $m += '- Ekkert. Þetta lagast sjálft. Ef það hefur ekki gerst fyrir áætlaðan dag kemur póstur merktur ÞARF ATHYGLI.'
} else {
    $m += '- Ekkert.'
}
if ($lifsmarkNu) {
    $okDagar = $vika.Lokid
    $m += ''
    $m += 'Vikuyfirlit:'
    $m += "- Næturuppfærslan kláraðist $okDagar af síðustu 7 nóttum."
    $m += '- Þessi póstur kemur alla mánudagsmorgna, líka þegar allt er í lagi. Komi hann ekki er vaktin sjálf biluð: segðu master frá því.'
}
# Fyrir lotur: tæknilínur, óbreyttar að efni.
$m += ''
$m += '______________________________'
$m += 'Fyrir lotur (tæknilínur):'
$m += $texti
if ($sopun.Count) {
    $s2 = $sopun
    if ($stig -ne 'athygli') { $s2 = @($sopun | ForEach-Object { $_ -replace '^(K\d) FALL', '$1 á eftir' -replace '^SOPUNARVAKT: FALL', 'SOPUNARVAKT: á eftir' }) }
    $m += ''; $m += 'Sópun (cc324):'; $m += $s2
}
if ($jafna.Count -and $keyrslur.Count) {
    $m += ''; $m += 'Síðustu keyrslur sópunar (lifecycle_sweep_runs.jsonl):'
    foreach ($r in $keyrslur) { $m += ('at={0} rent_cursor={1}/{2} sale_cursor={3}/{4} requests={5}' -f $r.at, $r.rent_cursor, $r.rent_total, $r.sale_cursor, $r.sale_total, $r.requests) }
}
if ($degrN -gt 0) {
    $orsakir = @(Get-Content -Encoding utf8 $nightLog | Where-Object { $_ -match '(?i)(WARN|FAIL|féll|villa|error|DEGRADED)' } | Select-Object -Last 12)
    if ($orsakir.Count) { $m += ''; $m += "Línur um það sem féll ($nightLog):"; $m += $orsakir }
}
if ($Prof -or $stada -ne 'LOKID') {
    $m += ''; $m += "Síðustu línur $($nightLog):"
    $m += @(Get-Content -Encoding utf8 $nightLog -Tail 8 -ErrorAction SilentlyContinue)
}
if ($frestad.Count) { $m += ''; $m += 'Frestslínur:'; $m += $frestad }
if ($lifsmarkNu) { $m += ''; $m += $vika.Haus; $m += $vika.Radir }
$meginmal = ($m -join "`n") + "`n"

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
