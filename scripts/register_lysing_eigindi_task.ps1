# Register-ScheduledTask for verdmat-nightly-lysing-eigindi (cc316b, GO Danna 05.11.2026).
# Run from an ELEVATED PowerShell if S4U registration is refused. Re-running is idempotent.
#
# Schedule: DAILY 06:10 local (== UTC on this box), per Danni 05.11. Runs only if tonight's night log ends on CHAIN CLEAN
#           (`--kedjuhlid`): waits for a running chain until 06:45, otherwise skips the night with a log line and no calls.
#           Calls stop at 06:53, clear of 06:55-07:05. Time limit 50 min > wait + run (WORKING_PROTOCOL (q)).
# Exit:     0 ok / 2 no key / 3 error / 4 gate refused the write / 6 cap or time stopped, queue left / 7 chain gate skipped the night.
#           public.lysing_eigindi stands unchanged on 3, 4 and 7.

$ErrorActionPreference = 'Stop'
$taskName  = 'verdmat-nightly-lysing-eigindi'
$pythonExe = 'C:\Python314\python.exe'
$scriptPy  = 'D:\verdmat-is\app\scripts\lysing_eigindi_nott.py'
$workDir   = 'D:\verdmat-is\app'
if (-not (Test-Path $pythonExe)) { throw "python missing: $pythonExe" }
if (-not (Test-Path $scriptPy))  { throw "script missing: $scriptPy" }
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument 'scripts\lysing_eigindi_nott.py --skrifa --kedjuhlid' -WorkingDirectory $workDir
$trigger = New-ScheduledTaskTrigger -Daily -At '06:10'
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 50)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false; "Unregistered existing $taskName" }
Register-ScheduledTask -TaskName $taskName -Description 'verdmat cc316b: LLM-lestur eiginda ur lysingu nyrra ibudaauglysinga i public.lysing_eigindi.' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -ErrorAction Stop | Out-Null
"Registered $taskName"
(Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime
