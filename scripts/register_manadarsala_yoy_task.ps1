# register_manadarsala_yoy_task.ps1 - cc251 f.2 (16.10.2026). Keyrist EINU SINNI ur HAEKKUDU PowerShell (Danni).
# Endurkeyrsla er idempotent. -Thurrt = thurrprof, skrair ekkert.
#
# VERK:  verdmat_manadarsala_yoy - scripts\cc251_manadarsala_yoy.py --skrifa gegnum
#        scripts\cc193_keyra_verk.ps1 -Verk manadarsala_yoy (logg D:\verdmat-is\logs\manadarsala_yoy.log).
#        Manadarsala a moti sama manudi i fyrra -> semantic.manadarsala_yoy (regla cc251-v1), /markadur Umsvifin.
# TIMI:  daglega kl. 05:15 - kaupskra lesin 02:30 (daily_sales_refresh); keyrarinn ber bidhlid a
#        verdmat-nightly-delta (<= 90 min), sama og fasteignasala_manudur. Keyrsla ~1 min (les kaupskra.csv).
# THAK:  3 klst (90 min bid + keyrsla + svigrum; laerdomur cc248: PT1H < bidhlid felldi verkid hljodlaust).
#        RestartCount 8 / PT30M (grippur raesingarbilun 0x8007010B eins og 14.10, cc240). IgnoreNew.
# LOGON: S4U (Password-principal fellur thogult - CLAUDE.md). RunLevel Limited.
# PYTHON: C:\Python314\python.exe (3.14.3; pandas 3.0.2, numpy 2.4.4, psycopg2 2.9.12 - sannreynt 16.10).
# ROLLBACK verks: Unregister-ScheduledTask -TaskName verdmat_manadarsala_yoy -Confirm:$false
# ROLLBACK gagna: supabase/rollback/20261016210000_cc251_manadarsala_yoy_rollback.sql
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'

$TaskName = 'verdmat_manadarsala_yoy'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\app\scripts\cc251_manadarsala_yoy.py'
$WorkDir  = 'D:\verdmat-is\app'

foreach ($p in @($PS, $Keyrari, $Python, $Skrift)) { if (-not (Test-Path $p)) { throw "vantar: $p (er cc251 pullad i D:\verdmat-is\app?)" } }
if (-not (Select-String -Path $Keyrari -Pattern "'manadarsala_yoy'" -SimpleMatch -Quiet)) { throw "keyrarinn thekkir ekki manadarsala_yoy - pulladu cc251 i D:\verdmat-is\app" }
$pyv = & $Python -c "import pandas, numpy, psycopg2, sys; print(sys.version.split()[0], pandas.__version__, numpy.__version__)"
if ($LASTEXITCODE -ne 0) { throw "python-pakkar vantar i $Python" }

$action = New-ScheduledTaskAction -Execute $PS `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk manadarsala_yoy') `
    -WorkingDirectory $WorkDir
$trigger   = New-ScheduledTaskTrigger -Daily -At '05:15'
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -RestartCount 8 -RestartInterval (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"adgerd:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
"trigger:   daglega kl. 05:15"
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"thak:      $($settings.ExecutionTimeLimit)  restart=$($settings.RestartCount)/$($settings.RestartInterval)  instances=$($settings.MultipleInstances)  wake=$($settings.WakeToRun)"
"python:    $Python ($pyv)"
if ($Thurrt) { "THURRPROF - ekkert skrad."; exit 0 }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskradi eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'cc251: manadarsala a moti sama manudi i fyrra -> semantic.manadarsala_yoy; daglega 05:15; logg D:\verdmat-is\logs\manadarsala_yoy.log' `
        -ErrorAction Stop | Out-Null
} catch {
    "SKRANING FELL: $($_.Exception.Message)"
    exit 1
}

$s = Get-ScheduledTask -TaskName $TaskName
$ok = ($s.Settings.ExecutionTimeLimit -eq 'PT3H') -and ($s.Settings.RestartCount -eq 8) -and `
      ($s.Settings.RestartInterval -eq 'PT30M') -and ($s.Principal.LogonType -eq 'S4U') -and `
      ($s.Actions[0].Arguments -like '*-Verk manadarsala_yoy*')
"SKRAD ${TaskName}: limit=$($s.Settings.ExecutionTimeLimit) rc=$($s.Settings.RestartCount)/$($s.Settings.RestartInterval) logon=$($s.Principal.LogonType)"
"naesta keyrsla: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
if ($ok) { 'OK'; exit 0 } else { 'FALL: stillingar stodust ekki'; exit 2 }
