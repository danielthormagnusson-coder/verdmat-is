# register_fasteignasala_task.ps1 - cc213 fasi 1 (27.09). Keyrist EINU SINNI ur HAEKKUDU PowerShell (Danni).
# Endurkeyrsla er idempotent. -Thurrt = thurrprof, skrair ekkert.
#
# VERK:  verdmat_fasteignasala_manudur - scripts\cc213_fasteignasala_manudur.py --sjalfvirkt gegnum
#        scripts\cc193_keyra_verk.ps1 -Verk fasteignasala_manudur (logg D:\verdmat-is\logs\fasteignasala_manudur.log).
#        Reiknar 2026-07 ... sidasta manud med aaetladri fullnustu >= 90 %: eignun per samning, nefnarar,
#        rodun stofa + sala (semantic.fasteignasala_manudur). Stada M-3 faerist sjalfkrafa i 'endanlegt'.
# TIMI:  16. hvers manadar kl. 04:30 - kaupskra 15. dags er lesin kl. 02:30 (daily_sales_refresh); keyrarinn
#        ber bidhlid a verdmat-nightly-delta (<= 90 min) thvi keyrslan les lika scraper.listings.
#        Fullnusta 15. M+1 maeld 91,8-97,8 % (SKIL_CC212 sec. 3); --sjalfvirkt velur manudinn sjalft.
# THAK:  1 klst (keyrsla ~3-5 min). IgnoreNew. WakeToRun + StartWhenAvailable.
# LOGON: S4U (Password-principal fellur thogult - CLAUDE.md). RunLevel Limited.
# ROLLBACK verks: Unregister-ScheduledTask -TaskName verdmat_fasteignasala_manudur -Confirm:$false
# ROLLBACK gagna: supabase/rollback/20260927180000_cc213_fasteignasala_manudur_rollback.sql
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'

$TaskName = 'verdmat_fasteignasala_manudur'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\app\scripts\cc213_fasteignasala_manudur.py'
$WorkDir  = 'D:\verdmat-is\app'

foreach ($p in @($PS, $Keyrari, $Python, $Skrift)) { if (-not (Test-Path $p)) { throw "vantar: $p" } }

$action = New-ScheduledTaskAction -Execute $PS `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk fasteignasala_manudur') `
    -WorkingDirectory $WorkDir
# ScheduledTasks-cmdlets hafa engan manadarlegan trigger: skrad fyrst med stakan trigger (cmdlets, S4U),
# svo er triggernum skipt ut fyrir TASK_TRIGGER_MONTHLY (4) gegnum COM Schedule.Service.
$trigger   = New-ScheduledTaskTrigger -Once -At '2026-10-16 04:30'
function Manadartrigger($def) {
    $def.Triggers.Clear()
    $tr = $def.Triggers.Create(4)          # TASK_TRIGGER_MONTHLY
    $tr.DaysOfMonth   = 32768              # bit 15 = 16. dagur
    $tr.MonthsOfYear  = 4095               # allir manudir
    $tr.StartBoundary = '2026-10-16T04:30:00'
    $tr.Enabled       = $true
    return $tr
}
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"adgerd:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
"trigger:   Monthly dagur 16 kl. 04:30 fra 2026-10-16 (COM, sja Manadartrigger)"
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"thak:      $($settings.ExecutionTimeLimit)  instances=$($settings.MultipleInstances)  wake=$($settings.WakeToRun)"
if ($Thurrt) {
    $svc = New-Object -ComObject Schedule.Service; $svc.Connect()
    $tr = Manadartrigger ($svc.NewTask(0))
    "COM-trigger (profadur, ekki skradur): type=$($tr.Type) DaysOfMonth=$($tr.DaysOfMonth) MonthsOfYear=$($tr.MonthsOfYear) start=$($tr.StartBoundary)"
    "THURRPROF - ekkert skrad."; exit 0
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskradi eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'cc213: manadarleg rodun fasteignasala (stofur + salar) -> semantic.fasteignasala_manudur; 16. kl. 04:30; logg D:\verdmat-is\logs\fasteignasala_manudur.log' `
        -ErrorAction Stop | Out-Null
    $svc = New-Object -ComObject Schedule.Service; $svc.Connect()
    $folder = $svc.GetFolder('\')
    $def = $folder.GetTask($TaskName).Definition
    Manadartrigger $def | Out-Null
    $folder.RegisterTaskDefinition($TaskName, $def, 4, $null, $null, 2) | Out-Null   # 4 = TASK_UPDATE, 2 = TASK_LOGON_S4U
    "SKRAD $TaskName (manadarlegur trigger, 16. kl. 04:30)"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    "naesta keyrsla: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRANING FELL: $($_.Exception.Message)"
    exit 1
}
