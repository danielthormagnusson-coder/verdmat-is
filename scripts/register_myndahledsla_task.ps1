# register_myndahledsla_task.ps1 — cc210 (27.09). Keyrist EINU SINNI úr HÆKKUÐU PowerShell (S4U-skráning
# krefst admin: „Access is denied" án). Endurkeyrsla er idempotent. -Thurrt = þurrpróf, skráir ekkert.
#
# VERK:  verdmat-nightly-myndahledsla — scripts\hlada_auglysingamyndir.py --skrifa gegnum
#        scripts\cc193_keyra_verk.ps1 -Verk myndahledsla (logg D:\verdmat-is\logs\myndahledsla.log).
#        Hleður R2-diskmanifestinu (myndamanifest/manifest/*.jsonl) í scraper.auglysingamyndir.
#        cc117 þrep 4 var aðeins handkeyrt 11.08 (0 -> 988.651) og aldrei tímasett; manifestið óx
#        um +129.160 slot eftir það (cc210 §5). Vélin er idempotent (ON CONFLICT + no-op-vörður cc210),
#        snertir ALDREI útilokunardálka (rétthafabeiðnir lifa), og jafnar rowcount == einkvæm slot
#        FYRIR commit (rc 2 = ROLLBACK, ekkert skrifað).
#
# TÍMI:  06:20 daglega. myndasaekjari (04:45) lauk 05:04–05:25 (hrinur.jsonl 26.–27.09); keyrarinn ber
#        auk þess BIÐHLIÐ á verdmat-nightly-myndasaekjari (Running -> bíða 2 mín, ≤90 mín).
# ÞAK:   2 klst. IgnoreNew. WakeToRun + StartWhenAvailable.
# LOGON: S4U (Password-principal fellur þögult — CLAUDE.md). RunLevel Limited.
# ROLLBACK verks: Unregister-ScheduledTask -TaskName verdmat-nightly-myndahledsla -Confirm:$false
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'

$TaskName = 'verdmat-nightly-myndahledsla'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\app\scripts\hlada_auglysingamyndir.py'
$WorkDir  = 'D:\verdmat-is\app'

foreach ($p in @($PS, $Keyrari, $Python, $Skrift)) { if (-not (Test-Path $p)) { throw "vantar: $p" } }

$action = New-ScheduledTaskAction -Execute $PS `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk myndahledsla') `
    -WorkingDirectory $WorkDir
$trigger   = New-ScheduledTaskTrigger -Daily -At 06:20
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

"verk:      $TaskName"
"aðgerð:    $($action.Execute) $($action.Arguments)"
"vinnum.:   $($action.WorkingDirectory)"
"trigger:   Daily $($trigger.StartBoundary)"
"principal: $($principal.UserId) $($principal.LogonType) $($principal.RunLevel)"
"þak:       $($settings.ExecutionTimeLimit)  instances=$($settings.MultipleInstances)  wake=$($settings.WakeToRun)"
if ($Thurrt) { "ÞURRPRÓF — ekkert skráð."; exit 0 }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false; "afskráði eldra $TaskName" }
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'cc210: R2-manifest -> scraper.auglysingamyndir (hlada_auglysingamyndir.py --skrifa, idempotent, jofnudur fyrir commit); 06:20 eftir myndasaekjara; logg D:\verdmat-is\logs\myndahledsla.log' `
        -ErrorAction Stop | Out-Null
    "SKRÁÐ $TaskName"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    "næsta keyrsla: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRÁNING FÉLL: $($_.Exception.Message)"
    exit 1
}
