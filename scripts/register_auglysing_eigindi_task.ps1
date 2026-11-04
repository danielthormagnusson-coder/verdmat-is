# Register-ScheduledTask for verdmat-nightly-auglysing-eigindi (cc316, GO Danna 04.11.2026).
# Re-running is idempotent. Removal: Unregister-ScheduledTask -TaskName verdmat-nightly-auglysing-eigindi
#
# Schedule: DAILY 06:40 local (== UTC on this box). After the night chain (worst case ~06:30) so
#           parsed_mbl.db is the night's final one; finished well before 06:55-07:05. A late chain
#           only means values one day old.
# What:     scripts/hlada_auglysing_eigindi.py --skrifa: reads scraper.v_eign_virk_auglysing and
#           parsed_mbl.db, updates public.auglysing_eigindi in one transaction (seconds).
#           Log: scraper_data/logs/auglysing_eigindi_YYYYMM.log
# Exit:     0 ok / 3 error / 4 gate refused the write. Table stands unchanged on 3 and 4.

$ErrorActionPreference = 'Stop'

$taskName  = 'verdmat-nightly-auglysing-eigindi'
$pythonExe = 'C:\Python314\python.exe'
$scriptPy  = 'D:\verdmat-is\app\scripts\hlada_auglysing_eigindi.py'
$workDir   = 'D:\verdmat-is\app'

if (-not (Test-Path $pythonExe)) { throw "python missing: $pythonExe" }
if (-not (Test-Path $scriptPy))  { throw "script missing: $scriptPy" }

$action = New-ScheduledTaskAction -Execute $pythonExe `
    -Argument 'scripts\hlada_auglysing_eigindi.py --skrifa' -WorkingDirectory $workDir
$trigger = New-ScheduledTaskTrigger -Daily -At '06:40'
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -WakeToRun -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    "Unregistered existing $taskName"
}
Register-ScheduledTask -TaskName $taskName `
    -Description 'verdmat cc316: ja-gildi ur reitum virkra mbl-auglysinga i public.auglysing_eigindi (birting i eigindaspjaldi).' `
    -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -ErrorAction Stop | Out-Null
"Registered $taskName"
Get-ScheduledTask -TaskName $taskName | Format-List TaskName, State
(Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime
