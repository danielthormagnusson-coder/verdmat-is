# cc336b (GO Danna 11.11.2026, G1): skráir verdmat-weekly-db-afrit.
# Sunnudagar 10:00 (vélin er á Greenwich Standard Time = UTC). Fjarri 03:00-næturafriti og utan 01:00–07:30;
# ef StartWhenAvailable ræsir verkið seint inn í bannglugga neitar backup_weekly_db.py sjálf (útgöngukóði 2).
# Mælt 11.11: pg_dump 958 s / 1,59 GB; þak 2 klst.
# Keyrir python beint; skriftan skrifar sjálf stdout/stderr í backup_log\vikulegt_<dags>_keyrsla.log.
# S4U krefst hækkaðra réttinda (sami veggur og cc102/cc111). Án hækkunar er skráð á Interactive
# (keyrir AÐEINS innskráð) og frávikið sagt hátt. Lagfæring í hækkuðu PowerShell:
#   & D:\verdmat-is\app\scripts\register_backup_weekly_task.ps1 -Endurskra
param([switch]$Endurskra)
$ErrorActionPreference = 'Stop'
$Nafn = 'verdmat-weekly-db-afrit'
$Skrifta = 'D:\verdmat-is\app\scripts\backup_weekly_db.py'
if (-not (Test-Path $Skrifta)) { throw "Skrifta vantar: $Skrifta" }
if (Get-ScheduledTask -TaskName $Nafn -ErrorAction SilentlyContinue) {
    if (-not $Endurskra) { throw "$Nafn er þegar til — HALT (notaðu -Endurskra til að skrá aftur)" }
    Unregister-ScheduledTask -TaskName $Nafn -Confirm:$false
}
$Act = New-ScheduledTaskAction -Execute 'C:\Python314\python.exe' -Argument $Skrifta -WorkingDirectory 'D:\verdmat-is\app'
$Trg = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At '10:00'
$Set = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
$Lys = 'cc336b: vikulegt pg_dump (app-skemu, án auth) + SQLite-skyndimyndir scraper_data (án parsed_mbl) -> R2 db_afrit/vikulegt/ (5 vikur)'
try {
    $Pri = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
    Register-ScheduledTask -TaskName $Nafn -Action $Act -Trigger $Trg -Settings $Set -Principal $Pri -Description $Lys -ErrorAction Stop | Out-Null
} catch {
    Write-Output "FRÁVIK: S4U hafnað (lota ekki hækkuð). Skráð á Interactive: keyrir AÐEINS innskráð."
    Write-Output "        Lagfæring í hækkuðu PowerShell: & '$PSCommandPath' -Endurskra"
    $Pri = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $Nafn -Action $Act -Trigger $Trg -Settings $Set -Principal $Pri -Description $Lys -ErrorAction Stop | Out-Null
}
$t = Get-ScheduledTask -TaskName $Nafn
"{0}  state={1}  logon={2}  next={3}" -f $Nafn, $t.State, $t.Principal.LogonType, (Get-ScheduledTaskInfo -TaskName $Nafn).NextRunTime
