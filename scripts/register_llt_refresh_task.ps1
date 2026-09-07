# register_llt_refresh_task.ps1 — cc180-TILLAGA (02.09) ENDURSKRIFUÐ cc193 (07.09). Keyrist EINU SINNI
# úr HÆKKUÐU PowerShell (Danni, HALT B). Endurkeyrsla er idempotent. -Thurrt = þurrpróf, skráir ekkert.
#
# VERK:  verdmat_llt_refresh — scripts\cc180_llt_refresh.py --revalidate gegnum scripts\cc193_keyra_verk.ps1
#        -Verk llt_refresh (logg D:\verdmat-is\logs\llt_refresh.log + D:\cc180_llt_refresh.log).
#        R1-b blöndun last_listing_text: evalue-raðir (frosið D:\last_listing_text.pkl) + lifandi mbl-raðir
#        úr scraper.listings → staging → 6 parity-hlið → atómískt rename-swap → hreinsun eldri ref-árganga
#        → POST /api/endurnyja {allt:true} (aðeins eftir FLIPP) svo /eign/[fastnum] beri nýja lind strax.
#
# TÍMI:  05:30 daglega — EKKI 03:45 eins og cc180 lagði til. Mælt í Task Scheduler-atburðaloggi 02.–07.09:
#        verdmat-nightly-delta (01:00, skrifar scraper.listings) lauk 04:14 / 04:15 / 04:03 / 04:55 / 02:40 /
#        02:46 — þ.e. var ENN Í KEYRSLU kl. 03:45 fjórar nætur af sex. sales-refresh (02:30) lýkur á
#        ~45–110 s, backup 03:00 á ~3 mín, myndasaekjari 04:45 lýkur 05:04–05:23 (snertir ekki
#        scraper.listings/last_listing_text). Lifecycle-sweep byrjar 06:00. 05:30 liggur því eftir öllum
#        lindum verksins og á undan sópuninni; keyrarinn ber að auki BIÐHLIÐ (bíður meðan delta er Running,
#        ≤90 mín) því keðjan hefur 8 klst þak og tímasetning ein er ekki hlið.
#
# SANNREYNT 07.09 (cc193): full handkeyrsla FLIPPAÐI (ref_20260907_1903, 67.518 raðir, 47 s) eftir að
#        parity-hlið [5] var lagað — lifandi raðir bera scraped_at = last_seen_at sem færist FRAM við hverja
#        sópun; hliðið dæmdi ásinn sjálfan sem misræmi (5 raðir, texti eins). Þurrpróf keyrara --no-flip OK.
# ÞAK:   2 klst (biðhlið ≤90 mín + keyrsla ~1 mín). IgnoreNew. WakeToRun + StartWhenAvailable.
# LOGON: S4U (Password-principal fellur þögult — CLAUDE.md). RunLevel Limited.
# ROLLBACK verks: Unregister-ScheduledTask -TaskName verdmat_llt_refresh -Confirm:$false
# ROLLBACK gagna: cc180_llt_flip.py skrifar D:\_audit\cc180_textathekja\cc180_rollback_<tag>.sql fyrir hvert flipp.
param([switch]$Thurrt)
$ErrorActionPreference = 'Stop'

$TaskName = 'verdmat_llt_refresh'
$PS       = 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe'
$Keyrari  = 'D:\verdmat-is\app\scripts\cc193_keyra_verk.ps1'
$Python   = 'C:\Python314\python.exe'
$Skrift   = 'D:\verdmat-is\app\scripts\cc180_llt_refresh.py'
$WorkDir  = 'D:\verdmat-is\app'

foreach ($p in @($PS, $Keyrari, $Python, $Skrift)) { if (-not (Test-Path $p)) { throw "vantar: $p" } }

$action = New-ScheduledTaskAction -Execute $PS `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -File "' + $Keyrari + '" -Verk llt_refresh') `
    -WorkingDirectory $WorkDir
$trigger   = New-ScheduledTaskTrigger -Daily -At 05:30
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
        -Description 'cc180/cc193: last_listing_text R1-b blondun (scraper.listings -> staging -> parity -> rename-swap) + revalidate; 05:30 eftir nightly-delta; logg D:\verdmat-is\logs\llt_refresh.log' `
        -ErrorAction Stop | Out-Null
    "SKRÁÐ $TaskName"
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
    "næsta keyrsla: " + (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
} catch {
    "SKRÁNING FÉLL: $($_.Exception.Message)"
    exit 1
}
