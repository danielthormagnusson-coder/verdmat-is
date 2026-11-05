# Register-ScheduledTask for verdmat-nightly-lysing-eigindi (cc316b). DRÖG: EKKI KEYRA ÁN GO DANNA.
# Run from an ELEVATED PowerShell if S4U registration is refused. Re-running is idempotent.
#
# Schedule: DAILY 05:30 local (== UTC on this box). After promote on a normal night (chain ends 02:40-04:50);
#           on the worst night (~06:30) it uses the previous night's ads, one day late. 10 min cap keeps it
#           clear of 06:55-07:05, and of the 06:40 task, which reads a different table.
# Exit:     0 ok / 2 no key / 3 error / 4 gate refused the write. public.lysing_eigindi stands unchanged on 3 and 4.

$ErrorActionPreference = 'Stop'
$taskName  = 'verdmat-nightly-lysing-eigindi'
$pythonExe = 'C:\Python314\python.exe'
$scriptPy  = 'D:\verdmat-is\app\scripts\lysing_eigindi_nott.py'
$workDir   = 'D:\verdmat-is\app'
if (-not (Test-Path $pythonExe)) { throw "python missing: $pythonExe" }
if (-not (Test-Path $scriptPy))  { throw "script missing: $scriptPy" }
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument 'scripts\lysing_eigindi_nott.py --skrifa' -WorkingDirectory $workDir
$trigger = New-ScheduledTaskTrigger -Daily -At '05:30'
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false; "Unregistered existing $taskName" }
Register-ScheduledTask -TaskName $taskName -Description 'verdmat cc316b: LLM-lestur eiginda ur lysingu nyrra ibudaauglysinga i public.lysing_eigindi.' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -ErrorAction Stop | Out-Null
"Registered $taskName"
(Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime
