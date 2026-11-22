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
#   cc350 (B1.3 cc347): RÉTTINDAVAKT. scripts/rettindavakt.py (aðeins lestur) mælir hvað anon/authenticated mega í
#       grunninum; reglan er að þau lesi aðeins semantic.fasteignasala_* ×3 + PostGIS. FALL → „þarf athygli“ á
#       mannamáli (hver getur hvað í hvaða hlut) + texti fyrir master; mæling sem mistekst líka. -RettindaSkra <skrá>:
#       les úttakið úr skrá (próf). Vaktarlínan ber rett=<rc>.
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
    [string]$SopunKeyrslur = 'D:\verdmat-is\scraper_data\lifecycle_sweep_runs.jsonl',
    [string]$RettindaSkra = '',         # cc350: úttak réttindavaktar úr skrá (próf og sýnishorn)
    [string]$SoluferliSkra = '',        # cc364: úttak soluferli_mv_stada.py úr skrá (próf)
    [string]$VoktunSkra = '',           # cc355: úttak voktun_stada.py úr skrá (próf)
    [string]$EndurraesingHermun = ''    # cc357: falsuð verkstaða fyrir/eftir endurræsingu (aðeins með -Thurrt)
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
# cc340: dagleg Lögbirtingasókn (eigið verk verdmat-daily-logbirting, 05:40, ekki í keðjunni). Les aðeins Task
# Scheduler-stöðu. Þarf athygli: keyrði ekki frá miðnætti, rc ekki 0, eða enn í gangi. Óskráð verk er aðeins nefnt.
#
# cc357 (WP (ak), GO Danna 20.11): EIN ENDURRÆSING við Smart App Control-lokun. Skilyrði, öll:
#   (1) verkið er á hvítlista $EndurHeimild (nú aðeins verdmat-daily-logbirting); næturkeðja og sópun eru á
#       bannlista og verða ALDREI endurræst héðan, hvað sem hvítlistinn segir;
#   (2) LastTaskResult = 4, síðasta keyrsla í dag, verkið ekki Running;
#   (3) „Application Control" í verkloggnum frá síðasta START-merki, EÐA CodeIntegrity-atburður 3077/3033 á
#       verdmat-is-skrá frá LastRunTime-5 s til LastRunTime+16 mín (rc 4 eitt og sér endurræsir ekki);
#   (4) ekki þegar endurræst í dag: ENDURRAESING-lína í $VaktLog fyrir dag+verk, eða fleiri en eitt START í
#       verkloggnum í dag (einhver keyrði það aftur) -> aldrei lykkja;
#   (5) tímaregla: á 01:00–07:30 UTC aðeins verk sem er sjálft næturverk á þeim tíma (NaeturVerk, logbirting 05:40),
#       og aldrei meðan næturkeðjan er I_GANGI. Utan gluggans: leyft (handvirk vakt að degi).
# Beðið er að hámarki $EndurBidSek eftir niðurstöðu (verkið er 2–30 s; vaktin ber 10 mín þak í Task Scheduler).
# Endurræsing sem tekst -> engin athygli (lína í tæknilínum + lbr=ok). Endurræsing sem fellur -> ÞARF ATHYGLI.
# -EndurraesingHermun <json> (aðeins með -Thurrt): falsar stöðu verksins fyrir/eftir og logg; kallar ALDREI
#   Start-ScheduledTask. Snið: {"fyrir":{"State","LastRunTime","LastTaskResult"},"eftir":{...},"log":"<skrá>","ce":false}
$EndurHeimild = @{ 'verdmat-daily-logbirting' = @{ Log = 'D:\verdmat-is\logs\logbirting.log'; Start = '=== START verk=logbirting '; NaeturVerk = $true } }
$EndurBann = @('verdmat-nightly-delta', 'verdmat-daily-lifecycle-sweep')
$EndurBidSek = 240
$hermun = $null
if ($EndurraesingHermun) {
    if (-not $Thurrt) { Write-Output 'EndurraesingHermun krefst -Thurrt'; exit 6 }
    $hermun = Get-Content -Raw -Encoding utf8 $EndurraesingHermun | ConvertFrom-Json
    $EndurHeimild['verdmat-daily-logbirting'].Log = $hermun.log
}
$hermunRaest = $false
function Get-VerkStada([string]$nafn) {
    if ($hermun) {
        $s = $(if ($hermunRaest) { $hermun.eftir } else { $hermun.fyrir })
        return [pscustomobject]@{ State = $s.State; LastRunTime = [datetime]$s.LastRunTime; LastTaskResult = [uint32]$s.LastTaskResult }
    }
    $v = Get-ScheduledTask -TaskName $nafn -ErrorAction Stop
    $i = $v | Get-ScheduledTaskInfo
    [pscustomobject]@{ State = [string]$v.State; LastRunTime = $i.LastRunTime; LastTaskResult = [uint32]$i.LastTaskResult }
}
function Test-SacLokun([string]$nafn, $info) {
    $h = $EndurHeimild[$nafn]
    if ($h.Log -and (Test-Path $h.Log)) {
        $linur = @(Get-Content -Encoding utf8 $h.Log -Tail 400)
        $si = -1
        for ($j = $linur.Count - 1; $j -ge 0; $j--) { if ($linur[$j].Contains($h.Start)) { $si = $j; break } }
        if ($si -ge 0 -and @($linur[$si..($linur.Count - 1)] | Where-Object { $_ -match 'Application Control' }).Count) { return 'logg' }
    }
    if ($hermun) { if ($hermun.ce) { return 'CodeIntegrity' } else { return '' } }
    try {
        $ce = @(Get-WinEvent -FilterHashtable @{ LogName = 'Microsoft-Windows-CodeIntegrity/Operational'; Id = 3077, 3033
                StartTime = $info.LastRunTime.AddSeconds(-5); EndTime = $info.LastRunTime.AddMinutes(16) } -ErrorAction Stop |
            Where-Object { $_.Message -match 'verdmat-is' })
        if ($ce.Count) { return 'CodeIntegrity' }
    } catch { }
    return ''
}
function Get-EndurBann([string]$nafn, $info) {
    if ($EndurBann -contains $nafn -or -not $EndurHeimild.ContainsKey($nafn)) { return 'ekki á hvítlista' }
    if ($info.State -eq 'Running') { return 'verkið í gangi' }
    if ($info.LastRunTime -lt $Nu.Date) { return 'fallið ekki frá í dag' }
    $d = $Nu.ToString('yyyyMMdd')
    if ((Test-Path $VaktLog) -and @(Get-Content -Encoding utf8 $VaktLog | Where-Object { $_ -match " ENDURRAESING dags=$d verk=$([regex]::Escape($nafn)) " }).Count) { return 'þegar endurræst í dag' }
    $h = $EndurHeimild[$nafn]
    if ($h.Log -and (Test-Path $h.Log)) {
        $dl = $Nu.ToString('yyyy-MM-dd')
        if (@(Get-Content -Encoding utf8 $h.Log -Tail 400 | Where-Object { $_.StartsWith($dl) -and $_.Contains($h.Start) }).Count -gt 1) { return 'þegar keyrt aftur í dag' }
    }
    $u = $Nu.ToUniversalTime().TimeOfDay
    if ($u -ge [timespan]'01:00' -and $u -lt [timespan]'07:30') {
        if (-not $h.NaeturVerk) { return 'næturgluggi 01:00–07:30 UTC' }
        if ($stada -eq 'I_GANGI') { return 'næturkeðjan í gangi' }
    }
    return ''
}
$lb = ''; $lbr = '-'
try {
    $lbNafn = 'verdmat-daily-logbirting'
    $lbInfo = Get-VerkStada $lbNafn
    $lbRc = [uint32]$lbInfo.LastTaskResult
    $lbHvad = $null
    if ($lbInfo.State -eq 'Running') { $lb = 'Lögbirting: enn í gangi kl. ' + $Nu.ToString('HH:mm'); $lbHvad = "Sókn Lögbirtingablaðsins (05:40) var enn í gangi kl. $($Nu.ToString('HH:mm'))." }
    elseif ($lbInfo.LastRunTime -lt $Nu.Date) { $lb = 'Lögbirting: keyrði ekki í dag (síðast ' + $lbInfo.LastRunTime.ToString('dd.MM HH:mm') + ')'; $lbHvad = 'Sókn Lögbirtingablaðsins (05:40) keyrði ekki í morgun.' }
    elseif ($lbRc -ne 0) {
        $lb = ('Lögbirting: rc 0x{0:X} kl. {1:HH:mm} (logg D:\verdmat-is\logs\logbirting.log)' -f $lbRc, $lbInfo.LastRunTime)
        $lbHvad = "Sókn Lögbirtingablaðsins (05:40) mistókst (rc $lbRc)."
        $sac = $(if ($lbRc -eq 4) { Test-SacLokun $lbNafn $lbInfo } else { '' })
        if ($sac) {
            $bann = Get-EndurBann $lbNafn $lbInfo
            if ($bann) {
                $lbr = 'bann'
                $lb += " — Smart App Control ($sac); ekki endurræst: $bann"
                $lbHvad = "Sókn Lögbirtingablaðsins (05:40) mistókst: Smart App Control lokaði skrá (rc 4). Vaktin endurræsti ekki ($bann)."
                Write-Output "ENDURRÆSING: ekki — $bann (rc 4, $sac)"
            } else {
                $raestKl = Get-Date
                if (-not $Thurrt) {
                    [IO.File]::AppendAllText($VaktLog, "$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) ENDURRAESING dags=$($Nu.ToString('yyyyMMdd')) verk=$lbNafn rc=$lbRc sac=$sac `r`n", $Utf8)
                    Start-ScheduledTask -TaskName $lbNafn -ErrorAction Stop
                    Start-Sleep -Seconds 3
                    $nyr = $null
                    while (((Get-Date) - $raestKl).TotalSeconds -lt $EndurBidSek) {
                        $nyr = Get-VerkStada $lbNafn
                        if ($nyr.State -ne 'Running' -and $nyr.LastRunTime -ge $raestKl.AddSeconds(-2)) { break }
                        Start-Sleep -Seconds 5
                    }
                } elseif ($hermun) {
                    $hermunRaest = $true
                    Write-Output "ENDURRÆSING (hermun): Start-ScheduledTask $lbNafn yrði kallað EINU SINNI (ekki kallað)"
                    $nyr = Get-VerkStada $lbNafn
                } else {
                    Write-Output "ENDURRÆSING (þurrt): myndi endurræsa $lbNafn einu sinni (rc 4, $sac) — ekkert kallað"
                    $nyr = $null
                }
                $kl = $raestKl.ToString('HH:mm')
                $nyrriEn = $(if ($hermun) { $lbInfo.LastRunTime.AddSeconds(1) } else { $raestKl.AddSeconds(-2) })
                if ($null -eq $nyr) { $lbr = 'thurrt' }
                elseif (($nyr.State -eq 'Running') -or ($nyr.LastRunTime -lt $nyrriEn)) {
                    $lbr = 'igangi'
                    $lb += " — Smart App Control ($sac); endurræst kl. $kl, ekki lokið eftir $EndurBidSek s"
                    $lbHvad = "Sókn Lögbirtingablaðsins (05:40) mistókst (Smart App Control, rc 4). Vaktin endurræsti hana kl. $kl en niðurstaða lá ekki fyrir eftir $([int]($EndurBidSek / 60)) mín."
                } elseif ([uint32]$nyr.LastTaskResult -eq 0) {
                    $lbr = 'ok'; $lbHvad = $null
                    $lb = "Lögbirting: OK eftir endurræsingu kl. $kl (05:40-keyrslan féll á rc 4, Smart App Control, $sac)"
                } else {
                    $lbr = 'fell'
                    $lb += (" — Smart App Control ({0}); endurræst kl. {1} og féll AFTUR (rc 0x{2:X})" -f $sac, $kl, [uint32]$nyr.LastTaskResult)
                    $lbHvad = "Sókn Lögbirtingablaðsins mistókst tvisvar: Smart App Control lokaði skrá kl. $($lbInfo.LastRunTime.ToString('HH:mm')) (rc 4) og endurræsing kl. $kl féll líka (rc $([uint32]$nyr.LastTaskResult))."
                }
                Write-Output "ENDURRÆSING: niðurstaða lbr=$lbr — $lb"
            }
        }
    }
    else { $lb = 'Lögbirting: OK kl. ' + $lbInfo.LastRunTime.ToString('HH:mm') }
    if ($lbHvad) {
        $mTexti = "verdmat-vakt $($dagur): $lb. Lestu D:\verdmat-is\logs\logbirting.log, finndu orsök og segðu mér hvað gerðist."
        if ($lbr -in 'fell', 'bann', 'igangi') { $mTexti += ' Smart App Control: lestu Microsoft-Windows-CodeIntegrity/Operational (Id 3033/3077) og fylgdu WP (ak); engin breyting á SAC án ákvörðunar Danna.' }
        $athygli += @{ Stutt = 'Lögbirtingasókn mistókst'
            Hvad = $lbHvad
            Thydir = 'Nýjar auglýsingar úr Lögbirtingablaðinu vantar í lb_auglysingar (hluthafar nota þær). Næsta keyrsla sækir síðustu 21 dag, svo gatið lokast sjálft þegar sóknin virkar á ný.'
            Master = $mTexti }
    }
} catch { if (-not $lb) { $lb = 'Lögbirting: verk ekki skráð' } else { $lb += ' — endurræsing brást: ' + $_.Exception.Message; $lbr = 'villa'
        $athygli += @{ Stutt = 'Lögbirtingasókn mistókst'; Hvad = "Sókn Lögbirtingablaðsins mistókst (rc 4, Smart App Control) og endurræsing brást: $($_.Exception.Message)"
            Thydir = 'Nýjar auglýsingar úr Lögbirtingablaðinu vantar í lb_auglysingar (hluthafar nota þær).'
            Master = "verdmat-vakt $($dagur): $lb. Fylgdu WP (ak)." } } }
# cc350: réttindavakt — opnu hlutverkin (anon/authenticated) mega aðeins lesa semantic.fasteignasala_* ×3 + PostGIS.
$rett = @(); $rettRc = 0
if ($RettindaSkra) {
    $rett = @(Get-Content -Encoding utf8 $RettindaSkra)
    $rl = ($rett | Where-Object { $_ -like 'RETTINDAVAKT:*' } | Select-Object -Last 1)
    $rettRc = $(if ($rl -like 'RETTINDAVAKT: OK*') { 0 } elseif ($rl -like 'RETTINDAVAKT: FALL*') { 1 } else { 3 })
} else {
    $fyrriKodun = [Console]::OutputEncoding; $fyrriPyUtf8 = $env:PYTHONUTF8
    try {
        $env:PYTHONUTF8 = '1'
        [Console]::OutputEncoding = $Utf8
        $rett = @(& 'C:\Python314\python.exe' (Join-Path $PSScriptRoot 'rettindavakt.py') 2>&1 | ForEach-Object { "$_" })
        $rettRc = $LASTEXITCODE
    } catch { $rett = @('RETTINDAVAKT: MÆLING MISTÓKST (ræsing)'); $rettRc = 3 }
    finally {
        [Console]::OutputEncoding = $fyrriKodun
        if ($null -eq $fyrriPyUtf8) { Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue } else { $env:PYTHONUTF8 = $fyrriPyUtf8 }
    }
}
$rettFravik = @($rett | Where-Object { $_ -like 'R *' } | ForEach-Object { $_.Substring(2) })
if ($rettRc -eq 1) {
    $athygli += @{ Stutt = 'gagnagrunnur opnari en á að vera'
        Hvad = ('Réttindavaktin fann {0} {1} í gagnagrunninum sem opni lykillinn eða innskráðir notendur eiga ekki að hafa: {2}' -f $rettFravik.Count, $(if ($rettFravik.Count -eq 1) { 'aðgang' } else { 'aðganga' }), ($rettFravik -join ' '))
        Thydir = 'Hver sem er með lykilinn úr vafranum (hann er opinber) gæti lesið eða breytt þessum gögnum beint, framhjá vefnum. Vefurinn sjálfur virkar eðlilega.'
        Master = "verdmat-vakt $($dagur): réttindavakt FALL ($($rettFravik.Count)): $($rettFravik -join ' ') Finndu hvaða skrifta eða migration veitti réttindin, leggðu til REVOKE og lagfæringu á orsökinni (HALT fyrir GO)." }
} elseif ($rettRc -ne 0) {
    $athygli += @{ Stutt = 'réttindavakt gat ekki mælt'
        Hvad = 'Vaktin gat ekki mælt hvaða aðgang opni lykillinn hefur í gagnagrunninum (tenging eða fyrirspurn brást).'
        Thydir = 'Óvíst hvort gagnagrunnurinn er opnari en hann á að vera; vefurinn sjálfur er ekki endilega fyrir áhrifum.'
        Master = "verdmat-vakt $($dagur): réttindavakt MÆLING MISTÓKST (rc $rettRc). Keyrðu scripts/rettindavakt.py og segðu mér hvað brást." }
}
# cc364: lind leitar (síðasta skref keðju og sópunar), flokkuð í EINU falli (scripts/soluferli_mv_stada.py).
# Ákvarðanir 21.11: OK = í lagi; SLEPPT = hvorki villa né grænt (fyrra skref féll og er hávært þar); FALL = „athygli“;
# VANTAR = hlutlaust (aldrei skráð, t.d. fyrir fyrstu keyrslu); VANTAR48 = „athygli“ (hefur verið skráð, ekkert í 48 klst.).
# 22.11 liður 7: MAELING_MISTOKST (staða ólesanleg úr grunni, eða ekkert SOLUFERLI_MV-úttak) = „athygli“.
if ($SoluferliSkra) { $sol = @(Get-Content -Encoding utf8 $SoluferliSkra) } else {
    $fyrriKodun3 = [Console]::OutputEncoding; $fyrriPyUtf83 = $env:PYTHONUTF8
    try {
        $env:PYTHONUTF8 = '1'; [Console]::OutputEncoding = $Utf8
        $sol = @(& 'C:\Python314\python.exe' (Join-Path $PSScriptRoot 'soluferli_mv_stada.py') 2>&1 | ForEach-Object { "$_" })
    } catch { $sol = @('SOLUFERLI_MV: nott=MAELING_MISTOKST sopun=MAELING_MISTOKST') }
    finally {
        [Console]::OutputEncoding = $fyrriKodun3
        if ($null -eq $fyrriPyUtf83) { Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue } else { $env:PYTHONUTF8 = $fyrriPyUtf83 }
    }
}
$solLinur = @($sol | Where-Object { $_ -like 'L *' } | ForEach-Object {
    $_.Substring(2) -replace '^(nott|sopun) OK ', '$1: í lagi, ' -replace '^(nott|sopun) SLEPPT ', '$1: sleppt, ' -replace '^(nott|sopun) FALL ', '$1: féll, ' -replace '^(nott|sopun) VANTAR48 ', '$1: vantar, ' -replace '^lestur MAELING_MISTOKST ', 'lestur: staðan ólesanleg úr grunni, ' })
$solBitar = (($sol | Where-Object { $_ -like 'SOLUFERLI_MV:*' } | Select-Object -Last 1) -replace '^SOLUFERLI_MV: ', '')
if (-not $solBitar) { $solBitar = 'nott=MAELING_MISTOKST sopun=MAELING_MISTOKST' }   # ekkert úttak = ólesanlegt (22.11 liður 7)
if ($solBitar -match '=(FALL|VANTAR48|MAELING_MISTOKST)' + [char]0x5C + 'b') {
    $athygli += @{ Stutt = 'lind leitar ekki endurnýjuð'
        Hvad = ('Endurnýjun á lista eigna á sölu sem leitin les féll, hefur ekki keyrt í 48 klst. eða staða hennar er ólesanleg úr grunni: {0}' -f ($solLinur -join ' · '))
        Thydir = 'Leitin og „Nýtt í vikunni“ sýna stöðuna frá síðustu heppnuðu endurnýjun. Dagafjöldi er réttur, en nýjustu breytingar á því hvaða eignir eru á sölu geta vantað.'
        Master = "verdmat-vakt $($dagur): soluferli_mv $solBitar. Lestu nýjustu raðir í public.pipeline_runs (run_type soluferli_mv_nott / soluferli_mv_sopun), finndu orsök og keyrðu scripts/endurnyja_soluferli_opin.py --thurrt áður en nokkuð er lagað (HALT fyrir GO)." }
}
# cc355 (ákvörðun 22.11 liður 5): ein lína „N áskriftir, M atburðir, K póstar“ síðasta sólarhring (scripts/voktun_stada.py,
# aðeins lestur). Breytir ekki stigi póstsins; ólesanlegt = lína sem segir það, hlutlaust.
if ($VoktunSkra) { $vok = @(Get-Content -Encoding utf8 $VoktunSkra) } else {
    $fyrriKodun4 = [Console]::OutputEncoding; $fyrriPyUtf84 = $env:PYTHONUTF8
    try {
        $env:PYTHONUTF8 = '1'; [Console]::OutputEncoding = $Utf8
        $vok = @(& 'C:\Python314\python.exe' (Join-Path $PSScriptRoot 'voktun_stada.py') 2>&1 | ForEach-Object { "$_" })
    } catch { $vok = @('VOKTUN: MAELING_MISTOKST raesing') }
    finally {
        [Console]::OutputEncoding = $fyrriKodun4
        if ($null -eq $fyrriPyUtf84) { Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue } else { $env:PYTHONUTF8 = $fyrriPyUtf84 }
    }
}
$vokL = ($vok | Where-Object { $_ -like 'VOKTUN:*' } | Select-Object -Last 1)
$voktunLina = $(if ($vokL -match 'askriftir=(\d+) atburdir=(\d+) postar=(\d+)') {
    'Vöktun síðasta sólarhring: {0} áskriftir, {1} atburðir, {2} póstar.' -f $Matches[1], $Matches[2], $Matches[3]
} else { 'Vöktun síðasta sólarhring: staðan ólesanleg úr grunni.' })
$stig = $(if ($athygli.Count) { 'athygli' } elseif ($jafna.Count) { 'jafna' } else { 'lagi' })

$postur = $Prof -or $lifsmarkNu -or (($Senda -or $Thurrt) -and $stig -ne 'lagi')

function Skra-Vakt([int]$r) {
    if ($Prof -or $Thurrt) { return }
    $lina = "$utc VAKT dags=$($Nu.ToString('yyyyMMdd')) kl=$($Nu.ToString('HH:mm')) stada=$stada frest=$($frestad.Count) rc=$r lifsmark=$lifsmarkStada sopun=$sopunRc rett=$rettRc degr=$degrN lb=$(if ($lb -like 'Lögbirting: OK*' -or $lb -like '*ekki skráð') { 'ok' } else { 'FALL' }) lbr=$lbr"
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
$m += ''
$m += $voktunLina   # cc355 liður 5
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
if ($lb) { $m += ''; $m += $lb }
if ($rett.Count) { $m += ''; $m += 'Réttindi (cc350):'; $m += $rett }
if ($solLinur.Count) { $m += ''; $m += 'Lind leitar (cc364):'; $m += $solLinur }
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
