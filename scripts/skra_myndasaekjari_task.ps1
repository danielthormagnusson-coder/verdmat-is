# skra_myndasaekjari_task.ps1 — cc111: skráir framvirku myndavélina í Task Scheduler.
#
# Regla: python-slóð er STAÐFEST ÁÐUR en skráð er (ekki eftir á), S4U-innskráning
# eins og hinar verdmat-vaktirnar, og glugginn er UTAN 01:00-03:30 (delta 01:00,
# myigloo 02:00, sales-refresh 02:30, backup 03:00).
#
# Keyrsla:  powershell -NoProfile -ExecutionPolicy Bypass -File <þessi skrá>
#           -WhatIf   -> sýnir hvað yrði gert, skráir ekkert

param(
    [string]$TaskName  = "verdmat-nightly-myndasaekjari",
    [string]$Timi      = "04:45",
    [string]$Python    = "C:\Python314\python.exe",
    [string]$Skrifta   = "D:\verdmat-is\app\scripts\myndasaekjari.py",
    [string]$Vinnumappa = "D:\verdmat-is\app",
    [int]$ThakMyndir   = 6000,
    [int]$ThakMin      = 60,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

Write-Output "=== FORSKOÐUN (allt staðfest FYRIR skráningu) ==="

# 1. python-slóðin — tilvist OG að hún svari
if (-not (Test-Path $Python)) { throw "python finnst ekki: $Python" }
$ver = & $Python -c "import sys; print(sys.version.split()[0])"
if ($LASTEXITCODE -ne 0) { throw "python svarar ekki: $Python" }
Write-Output ("  python      : {0}  (v{1})" -f $Python, $ver)

# 2. skriftan og að hún þýðist
if (-not (Test-Path $Skrifta)) { throw "skrifta finnst ekki: $Skrifta" }
& $Python -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" $Skrifta
if ($LASTEXITCODE -ne 0) { throw "skriftan þýðist ekki: $Skrifta" }
Write-Output ("  skrifta     : {0}  (þýðist)" -f $Skrifta)

# 3. innfluttar einingar sem keyrslan hvílir á
& $Python -c "import curl_cffi, psycopg2, jsonschema"
if ($LASTEXITCODE -ne 0) { throw "vantar einingu (curl_cffi / psycopg2 / jsonschema)" }
Write-Output "  einingar    : curl_cffi, psycopg2, jsonschema OK"

# 4. rclone + config
foreach ($p in @("D:\verdmat-is\tools\rclone\rclone.exe", "D:\verdmat-is\tools\rclone\rclone.conf")) {
    if (-not (Test-Path $p)) { throw "vantar: $p" }
}
Write-Output "  rclone      : OK"

# 5. vísirinn verður að vera sáður — annars telur sækjarinn allt safnið ósótt
$visir = "D:\verdmat-is\scraper_data\myndamanifest\myndavisir.db"
if (-not (Test-Path $visir)) { throw "vísirinn vantar ($visir). Keyrðu --endurbyggja-visi fyrst." }
$n = & $Python -c "import sqlite3;print(sqlite3.connect(r'$visir').execute('select count(*) from sha_geymd').fetchone()[0])"
if ([int]$n -lt 1000) { throw "vísirinn er nánast tómur ($n sha). Keyrðu --endurbyggja-visi fyrst." }
Write-Output ("  vísir       : {0} sha geymd" -f $n)

# 6. glugginn má ekki lenda í 01:00-03:30
$hh, $mm = $Timi.Split(":")
$minutur = [int]$hh * 60 + [int]$mm
if ($minutur -ge 60 -and $minutur -le 210) { throw "tíminn $Timi er inni í banngluggnum 01:00-03:30" }
Write-Output ("  gluggi      : {0} (utan 01:00-03:30)" -f $Timi)

$arg = "$Skrifta --framvirkt --thraedir-mbl 1 --thraedir-myigloo 4 " +
       "--thak-myndir $ThakMyndir --thak-min $ThakMin"
Write-Output ""
Write-Output "=== SKRÁNING ==="
Write-Output ("  task   : {0}" -f $TaskName)
Write-Output ("  exec   : {0}" -f $Python)
Write-Output ("  args   : {0}" -f $arg)
Write-Output ("  wd     : {0}" -f $Vinnumappa)
Write-Output ("  daglega: {0}  S4U/danie" -f $Timi)

if ($WhatIf) { Write-Output "`n-WhatIf: ekkert skráð."; exit 0 }

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Output "  (til fyrir — afskrái og skrái aftur)"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$action  = New-ScheduledTaskAction -Execute $Python -Argument $arg -WorkingDirectory $Vinnumappa
$trigger = New-ScheduledTaskTrigger -Daily -At $Timi
$set     = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun `
             -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
             -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 30) `
             -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

# S4U krefst HÆKKAÐRA réttinda (sama veggur og cc102 rakst á). Ef lotan er ekki
# hækkuð fellur skráningin á Interactive — verkið keyrir þá AÐEINS innskráð.
# Það er frávik og er sagt hátt, ekki þagað yfir.
$s4u = $true
try {
    $princ = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
        -Principal $princ -Settings $set -ErrorAction Stop | Out-Null
} catch {
    $s4u = $false
    Write-Output ""
    Write-Output "  !! S4U-skraning hafnad (adgangur bannadur - lotan er ekki hoekkud)."
    Write-Output "  !! Skrai a INTERACTIVE i stadinn. Verkid keyrir tha AÐEINS innskrad."
    Write-Output "  !! Lagfaering: keyrdu D:\cc111_fix_s4u.ps1 i hoekkudum PowerShell."
    $princ = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
        -Principal $princ -Settings $set -ErrorAction Stop | Out-Null
}

$t = Get-ScheduledTask -TaskName $TaskName
$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Output ""
Write-Output "=== SKRÁÐ ==="
Write-Output ("  state   : {0}" -f $t.State)
Write-Output ("  logon   : {0}" -f $t.Principal.LogonType)
Write-Output ("  next    : {0}" -f $i.NextRunTime)
Write-Output ("  exec    : {0} {1}" -f $t.Actions[0].Execute, $t.Actions[0].Arguments)
if (-not $s4u) {
    Write-Output ""
    Write-Output "  FRAVIK: logon=Interactive, ekki S4U. Verkid keyrir EKKI utinnskrad."
    Write-Output "          Keyrdu D:\cc111_fix_s4u.ps1 i hoekkudum PowerShell til ad loka thessu."
    exit 10
}
