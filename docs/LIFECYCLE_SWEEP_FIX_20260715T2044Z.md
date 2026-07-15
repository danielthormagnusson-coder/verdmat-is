# LIFECYCLE-SWEEP BILUN — rótargreining og lagfæring (cc3)

**UTC-stimpill:** 2026-07-15T20:44Z · **Klukka sannreynd:** local = UTC (2026-07-15T20:04:24Z)
**Verk:** `verdmat-daily-lifecycle-sweep` (Task Scheduler, S4U, 06:00 GMT daglega)
**Einkenni:** LastTaskResult `0x8007010B` ("The directory name is invalid"); 11.995 absent-flaggaðar mbl-sale raðir biðu escalation.

## 1. Rótarorsök: BitLocker-læst D: eftir Windows Update-endurræsingu

`D:` er BitLocker-varið og aflæsist ekki fyrr en notandi skráir sig inn. Windows Update
endurræsti vélina kl. **05:29–05:34** bæði **11.07** og **15.07** (System-log 1074/6005/6006,
MoUsoCoreWorker + TrustedInstaller). Kl. 06:00:01 reyndi scheduler að ræsa
`C:\Python314\python.exe` með `WorkingDirectory=D:\verdmat-is\app` á **læstu** drifi →
CreateProcess skilar `0x8007010B`.

Reykbyssan (BitLocker Management-log, 15.07):

    07:52:24 — Event 782: "The BitLocker protected volume D: was unlocked."

þ.e. D: var læst 05:34→07:52 — 06:00-glugginn lenti inni í því bili.

**Af hverju bara þetta verk:** hin verkin (delta 01:00, myigloo 02:00, sales-refresh 02:30,
backup 03:00) keyra á undan WU-endurræsingarglugganum (~05:30) og sluppu bæði skiptin.
Sama python.exe + sama WorkingDirectory + sama S4U-principal gekk 0x0 sömu nótt kl. 02:30.

**Tímalína:** 11.07 = launch-fail (reboot 05:29) · 12.07 = heilbrigð rent-lota (síðustu events) ·
13.–14.07 = heilbrigðar no-op keyrslur (ekkert due; state-skráin skrifuð 14.07 06:00:03) ·
15.07 = launch-fail (reboot 05:29) — einmitt fyrsta nóttin sem sale-runa 2 var due (varð due 14.07 16:48).

## 2. Aukafundur: KillSwitch-exit týnir traceback-i (exit 0x1)

Handkeyrsla um scheduler kl. 20:18Z fraus rununa (26.612 id) en dó á ~1 sek með exit 1 —
stakt transient (ein 403/GraphQL-villa/pooler-blip → KillSwitch, sem er viljandi hársár;
resume-safe by design). Endurtekning kl. 20:37Z dó líka — sjálfskaparvíti: gagnvirk
greiningarkeyrsla var enn á lífi (tvöfalt instance → samtímis-queries). Þriðja
scheduler-keyrslan (20:44Z→) gengur heilbrigt. **Engin deterministic villa í skriptunni.**

Traceback fór þó í ósýnilegan stderr í öllum tilvikum. **Lagfæring (skrifuð):**
`scripts/lifecycle_sweep_mbl.py` `__main__`-blokkin skrifar nú unhandled-exception
traceback í `D:\verdmat-is\scraper_data\lifecycle_sweep_error.log` (append) áður en hún
re-raise-ar. Engin breyting á sweep-/escalation-lógík.

## 3. Handkeyrsla og escalation-sannprófun (fyrir/eftir)

Fyrir (20:12Z): active mbl-sale 26.612 · **pending escalation 11.995** · withdrawn_confirmed 180.
Runa 2 fryst 20:18Z (26.612 id = 1.664 requests á PAGE=16). Eftir 9 batches (144 id, 20:39Z):

| mæling | fyrir | eftir 144 id |
|---|---|---|
| pending escalation (mbl-sale) | 11.995 | 11.852 |
| withdrawn_confirmed alls | 180 | 323 (+143) |
| confirmed_absent_1 ný | — | 0 |

**143/144 fyrstu id escalatuðu strax** — round-1 absent-bylgjan klasast á lágum listing_id.
Vikubilskrafan er uppfyllt gagnvart öllum 11.995 (prior absent frá runu 1, 04.–07.07, >7 d).
Leysist því **jafnóðum og cursor nær þeim**, ekki á næstu vikum: ~360 requests/nótt (12h-þak
á 120s spacing) = ~5.760 id/nótt → runan klárar á ~4,6 nóttum, **öll 11.995 escalatuð eigi
síðar en ~20.07** (þau sem enn eru fjarverandi; þau sem birtast aftur teljast found).

## 4. Staða scheduler-verksins

- 20:44Z: keyrsla um scheduler LIFANDI (State=Running), resume frá cursor 144.
- Next Run Time: 16.07 06:00 GMT. ATH: næturkeyrslan í kvöld deyr á 12h-þakinu (~08:45Z á
  morgun, LastResult 0x41306) — **by design** (per-batch resume; docstring: "a WU-kill resumes
  next run losing at most the in-flight batch"). 16.07 06:00-trigger verður sleppt (IgnoreNew,
  instance enn í gangi) — engin nettó-töf; resume 17.07 06:00.
- `0x0` sem Last Result sést aðeins á no-op/runulokanóttum; mid-round nætur enda á 0x41306.

## 5. Það sem bíður elevation (Danni: eitt elevated PowerShell)

Set-ScheduledTask á S4U-verki og BitLocker-skipanir krefjast admin (Access denied úr
óupphækkaðri skel; sudo til en óvirkt). Í elevated PowerShell:

```powershell
# A) Config-fix: endurræsi verkið sjálfkrafa þar til D: aflæsist (8 x 30 mín = til 10:00)
$t = Get-ScheduledTask 'verdmat-daily-lifecycle-sweep'
$t.Settings.RestartCount = 8
$t.Settings.RestartInterval = 'PT30M'
Set-ScheduledTask -InputObject $t

# B) RÓTARFIX (valkvætt, öryggisákvörðun): D: aflæsist sjálfkrafa við boot
#    (lykill geymdur á C: sem TPM aflæsir; D: þá opið án innskráningar — þín ákvörðun)
manage-bde -autounlock -enable D:

# C) Framtíðar-greinanleiki: kveikja á Task Scheduler-atburðaskránni
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true
```

A dugar eitt og sér ef þú skráir þig inn fyrir ~10:00 eftir WU-nætur; B lagar líka
útsetningu HINNA næturverkanna fyrir WU-endurræsingum fyrir 01:00–03:00 (sama gildra,
bara ósprungin þar enn). WU-endurræsingar mældust ~05:30 tvisvar (11.07, 15.07) — WU-pásu-
resepta (HKLM, max 35 d) er til en er ekki varanleg vörn.

## 6. Breytingar þessarar lotu

- `scripts/lifecycle_sweep_mbl.py`: traceback-skráning í `__main__` (observability, engin lógík). Committað eftir go 15.07.
- Þetta skjal. Engin DB-skemabreyting; öll DB-skrif voru venjuleg sweep-rekstrargögn (append).
- Tímabundið greiningarverk `cc3-sweep-diag` var skráð og **fjarlægt** (residue = 0).

## 7. Lokastaða elevation-atriðanna (go-svar eiganda, 15.07)

- **A (restart-on-failure)** og **C (Task Scheduler-loggur)**: Danni keyrir sjálfur upphækkað.
- **B (BitLocker autounlock á D:)**: **MEÐVITAÐ OPIN ákvörðun hjá eiganda** — öryggis-
  ávinningur (D: læst án innskráningar) veginn á móti rekstraráhættunni. Afleiðing á meðan
  óákveðið er: **næturverk sem keyra fyrir innskráningu falla eftir WU-endurræsingu** — öll
  verk með WD/gögn á D: (01:00 delta, 02:00 myigloo, 02:30 sales-refresh, 03:00 backup,
  06:00 sweep) eru útsett ef WU endurræsir á undan þeim; restart-config (A) mildar aðeins
  gluggann fram að innskráningu. Ákvörðunin liggur hjá Danna.
