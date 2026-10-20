# keyra_i_verkhlut.ps1 — cc268 (c), úr tillögu cc265 (ókeyrð í raunverki þar til admin_cc268.ps1 skrefi C er beitt) — keyrir skipun inni í Windows Job Object með
# JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, svo að þegar Task Scheduler stöðvar verkið (ExecutionTimeLimit,
# atburður 329, eða Stop/End) deyr ALLT ferlatréð: Git\bin\bash.exe -> usr\bin\bash.exe -> python.
#
# Mælt í cc265 (prof\prof_ferlatre*.log): Task Scheduler drepur aðeins rótarferlið. Hvorki
# Git\bin\bash.exe (A) né usr\bin\bash.exe (B) sem rót dugar — MSYS býr til annað bash-ferli og
# python lifir. Þessi umbúðaskrift er rótin; hún setur SJÁLFA SIG í verkhlutinn áður en hún ræsir
# barnið, svo öll afkvæmi erfa aðildina. Deyi umbúðirnar (hvernig sem er) lokast síðasta
# handfangið og kjarninn drepur alla meðlimi.
#
# Notkun (verkaðgerð):
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File <slóð>\keyra_i_verkhlut.ps1
#       -Skipun 'C:\Program Files\Git\bin\bash.exe' -Rok "-lc \"/d/verdmat-is/app/scripts/nightly_delta_chain.sh\""
#   (ATH: -File les EKKI einfaldar gæsalappir sem tilvitnun — tvöfaldar með \" inni, mælt í cc265 C1)
# Exit-kóði = exit-kóði barnsins (Task Scheduler LastTaskResult les hann óbreyttan).
param(
    [Parameter(Mandatory = $true)][string]$Skipun,
    [string]$Rok = ''
)
$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Verkhlutur {
    [StructLayout(LayoutKind.Sequential)]
    struct BASIC { public long a, b; public uint LimitFlags; public UIntPtr c, d; public uint e; public UIntPtr f; public uint g, h; }
    [StructLayout(LayoutKind.Sequential)]
    struct IOC { public ulong a, b, c, d, e, f; }
    [StructLayout(LayoutKind.Sequential)]
    struct EXT { public BASIC Basic; public IOC Io; public UIntPtr p, j, pp, jp; }
    [DllImport("kernel32.dll", SetLastError = true)] static extern IntPtr CreateJobObject(IntPtr a, string n);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool SetInformationJobObject(IntPtr j, int c, ref EXT i, uint l);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool AssignProcessToJobObject(IntPtr j, IntPtr p);
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
    public static IntPtr Handfang;   // haldið lifandi út ævi ferlisins; aldrei lokað viljandi
    public static void SetjaSjalfan() {
        Handfang = CreateJobObject(IntPtr.Zero, null);
        if (Handfang == IntPtr.Zero) throw new Exception("CreateJobObject " + Marshal.GetLastWin32Error());
        EXT i = new EXT(); i.Basic.LimitFlags = 0x2000;   // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if (!SetInformationJobObject(Handfang, 9, ref i, (uint)Marshal.SizeOf(typeof(EXT))))
            throw new Exception("SetInformationJobObject " + Marshal.GetLastWin32Error());
        if (!AssignProcessToJobObject(Handfang, GetCurrentProcess()))
            throw new Exception("AssignProcessToJobObject " + Marshal.GetLastWin32Error());
    }
}
'@
[Verkhlutur]::SetjaSjalfan()

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $Skipun
$psi.Arguments = $Rok
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true   # eigin falin leikjatölva: barnið fær ekki CTRL_CLOSE frá glugga umbúðanna (cc265 C1: 0xC000013A eftir 6–16 s án þessa)
$p = [System.Diagnostics.Process]::Start($psi)
$p.WaitForExit()
exit $p.ExitCode
