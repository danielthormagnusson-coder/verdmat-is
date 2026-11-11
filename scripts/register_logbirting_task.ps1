# register_logbirting_task.ps1 — cc340 (11.11.2026). Skráir verdmat-daily-logbirting 05:40. Idempotent; -Thurrt skráir ekkert.
#
# VERK:   dagleg Lögbirtingasókn -> public.lb_auglysingar, áður skýjaverk (náði ekki lengur í repo, síðasta sókn 02.11).
#         cc193_keyra_verk.ps1 -Verk logbirting -> D:\verdmat-is\logbirting\.venv python keyra_dagleg.py --thak-min 10
#         (repo logbirting á föstum commit af main). Sjálfstætt verk, EKKI skref í næturkeðjunni.
# TÍMI:   05:40 (vélin á GMT = UTC). Mælt 11.11: 10 tölublöð/11 beiðnir á 39 s; dagleg keyrsla 1-2 tölublöð + ~15
#         sleppt (1,3 s hvert) = um 1 mín. Ekkert annað verk 05:40-06:00; sópun 06:00, lýsing 06:10, auglýsing 06:40,
#         vakt 07:00 (les stöðu þessa verks, bilun í vaktarpóst), þekjupróf 07:15, status 07:30, utflutt-myndir 07:35.
# ÞAK:    15 mín (verk) > 10 mín (keyra_dagleg, drepur allt ferlatréð með taskkill /T). Þak verksins drepur aðeins
#         keyrarann; innra þakið tryggir að python og barnaferli deyi. Engin StartWhenAvailable: missi vélin 05:40
#         keyrir verkið ekki á öðrum tíma; vaktin 07:00 tilkynnir „keyrði ekki“ og 21 dags gluggi næsta dags nær gatinu.
# KÓÐAR:  0 í lagi · 1 villa í tölublaði · 4 samantekt vantar · 6 innra tímaþak · 7 ekkert tölublað (API/lokun).
#         3 ekki notaður (status-probe telur 3 gott).
# LOGG:   D:\verdmat-is\logs\logbirting.log (keyrarinn).
# LOGON:  S4U, RunLevel Limited. Skráning S4U krefst stjórnandaréttinda: Danni keyrir sem admin.
# BAKFÆRSLA: Unregister-ScheduledTask -TaskName verdmat-daily-logbirting -Confirm:$false
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'
$TaskName = 'verdmat-daily-logbirting'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$WorkDir  = 'D:\verdmat-is\logbirting\scraper'
$Venv     = 'D:\verdmat-is\logbirting\.venv\Scripts\python.exe'
$Skrift   = 'D:\verdmat-is\logbirting\scraper\keyra_dagleg.py'
foreach ($p in @($PS, $Keyrari, $Venv, $Skrift, 'D:\verdmat-is\.dbconfig')) { if (-not (Test-Path $p)) { throw "vantar: $p" } }
if (-not (Select-String -Path $Keyrari -Pattern "'logbirting'" -Quiet)) { throw "keyrarinn þekkir ekki -Verk logbirting (ff app main fyrst)" }

$action = New-ScheduledTaskAction -Execute $PS -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk logbirting') -WorkingDirectory $WorkDir
$trigger = New-ScheduledTaskTrigger -Daily -At '05:40'
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -MultipleInstances IgnoreNew `
    -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"adgerd:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
"trigger:   Daily $($trigger.StartBoundary)"
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"thak:      $($settings.ExecutionTimeLimit)  instances=$($settings.MultipleInstances)  wake=$($settings.WakeToRun)  startWhenAvailable=$($settings.StartWhenAvailable)"
if ($Thurrt) { 'ÞURRPRÓF: ekkert skráð.'; exit 0 }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskráði eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'cc340: dagleg Lögbirtingasókn í public.lb_auglysingar (21 dags gluggi), 05:40; logg D:\verdmat-is\logs\logbirting.log' `
        -ErrorAction Stop | Out-Null
    "SKRÁÐ $TaskName"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    'næsta keyrsla: ' + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRÁNING FÉLL: $($_.Exception.Message)"
    exit 1
}
