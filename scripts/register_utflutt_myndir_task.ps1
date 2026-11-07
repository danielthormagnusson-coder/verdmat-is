# register_utflutt_myndir_task.ps1 - cc325 (07.11.2026). Endurkeyrsla er idempotent. -Thurrt skrair ekkert.
#
# VERK:   verdmat-daily-utflutt-myndir: scripts\cc325_endurnyja_utflutt_myndir.py, sem eigandi verdmat.
#         Endurnyjar registur_utflutningur.utflutt_eign_myndir, eina syn.
# TIMI:   07:35 (velin a GMT), eftir banntima 01:00-07:30.
# THAK:   30 min: 900 s REFRESH, tvaer talningar og forathugun, 120 s hver. Python er rotarferlid.
# KODAR:  rc i skriftunni. Status-probe les LastTaskResult verdmat-* verka, og 3 telst gott, svo 3 er ekki notadur.
# LOG:    D:\verdmat-is\logs\utflutt_myndir.log
# LOGON:  S4U (Password-principal fellur thogult, CLAUDE.md). RunLevel Limited.
# BAKFAERSLA: Unregister-ScheduledTask -TaskName verdmat-daily-utflutt-myndir -Confirm:$false
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'

$TaskName = 'verdmat-daily-utflutt-myndir'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\app\scripts\cc325_endurnyja_utflutt_myndir.py'
$WorkDir  = 'D:\verdmat-is\app'

foreach ($p in @($Python, $Skrift)) { if (-not (Test-Path $p)) { throw "vantar: $p" } }

$action = New-ScheduledTaskAction -Execute $Python -Argument 'scripts\cc325_endurnyja_utflutt_myndir.py' -WorkingDirectory $WorkDir
$trigger = New-ScheduledTaskTrigger -Daily -At '07:35'
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"adgerd:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
"trigger:   Daily $($trigger.StartBoundary)"
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"thak:      $($settings.ExecutionTimeLimit)  instances=$($settings.MultipleInstances)  wake=$($settings.WakeToRun)"
if ($Thurrt) { 'THURRPROF: ekkert skrad.'; exit 0 }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskradi eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'cc325: endurnyjar registur_utflutningur.utflutt_eign_myndir sem eigandi verdmat, 07:35 eftir vakt; logg D:\verdmat-is\logs\utflutt_myndir.log' `
        -ErrorAction Stop | Out-Null
    "SKRAD $TaskName"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    'naesta keyrsla: ' + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRANING FELL: $($_.Exception.Message)"
    exit 1
}
