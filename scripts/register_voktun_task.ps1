# register_voktun_task.ps1 — cc320. Skráir verdmat-daily-voktun 08:00. Rollback: Unregister-ScheduledTask -TaskName verdmat-daily-voktun -Confirm:$false
# 08:00: eftir keðju (05:30), Verðvakt (06:45), vakt og nybygging (07:00), þekjupróf (07:15), status (07:30), cvakt (07:45). Ekkert annað verk 08:00.
# Póstur fer aðeins á ABENDING_MOTTAKANDI nema VOKTUN_OPID=1 (opnun, GO Danna). -Thurrt = þurrpróf, skráir ekkert.
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'
$TaskName = 'verdmat-daily-voktun'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$WorkDir  = 'D:\verdmat-is\app'
foreach ($p in @($PS, $Keyrari)) { if (-not (Test-Path $p)) { throw "vantar: $p" } }
$action = New-ScheduledTaskAction -Execute $PS -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk voktun') -WorkingDirectory $WorkDir
$trigger = New-ScheduledTaskTrigger -Daily -At 08:00
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
"verk: $TaskName  08:00  $($action.Arguments)"
if ($Thurrt) { "ÞURRPRÓF: ekkert skráð."; exit 0 }
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'cc320: vöktun með tölvupósti; hvítlisti meðan rofi er af' -ErrorAction Stop | Out-Null
    "SKRÁÐ $TaskName; næsta: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch { "SKRÁNING FÉLL: $($_.Exception.Message)"; exit 1 }
