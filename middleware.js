/**
 * ALLSHERJAR-LOKUN — ÞETTA REPÓ BIRTIR EKKERT (cc159, 14.08.2026).
 * ============================================================================
 * `D:\verdmat-is\app` er FROSINN SPEGILL. Lifandi vefurinn er `verdmat-ai`
 * (**www.verdmat.ai**); þetta repó stendur áfram sem KÓÐAHEIMILD í git en á
 * engan notendaflöt. Þangað til í dag var það samt í loftinu á
 * `verdmat-is.vercel.app` sem heil ÖNNUR ÚTGÁFA af afurðinni: `/` og
 * `/eign/[fastnum]` svöruðu 200 með maí-tölum („Uppfært: maí 2026 · 124.835
 * eignir“), `/ops` bar tvífara rekstrarborðsins og **ekkert `robots.txt` var
 * til**. Sjá DECISIONS §5D-14 lið 6.
 *
 * Hvert einasta svar er nú **404** — engin síða, engin gögn, ekkert API.
 * Þetta er BIRTINGARLOKUN, ekki eyðing: kóðinn, sagan og migrationirnar standa
 * óbreytt í git og hver sem er getur lesið þau hér.
 *
 * ── HVERS VEGNA ÞESSI LEIÐ EN EKKI VERCEL-STILLING ─────────────────────────
 * Fyrsti kostur borðsins (T1) var Vercel Authentication á „All Deployments",
 * sem ver líka framleiðslulénið. Sá kostur **féll á verði**: hann er á bak við
 * $150/mán greiðsluvegg og rekstrarlega verðlaus hér, því markmiðið er ekki
 * aðgangsstýring heldur að tvífarinn hætti að birtast. „Standard Protection",
 * sem er innifalin, undanskilur einmitt framleiðslulénið og gerir því ekkert
 * gagn í þessu tilviki.
 *
 * ── AFTURKRÆFNI ────────────────────────────────────────────────────────────
 * Ein `git revert` skilar bæði fyrri hegðun OG gamla hliðunum. Það sem þessi
 * skrá bar áður — `OPS_PASSWORD`-hliðið á `/ops` og Supabase-`pro_users`-hliðið
 * á `/pro` — er í sögunni; `/ops` var flutt í `verdmat-ai` (`proxy.ts`) í cc159
 * og er ekki lengur til hér.
 *
 * Matcher-inn er `/:path*` af ásettu ráði: EKKERT er undanskilið, hvorki
 * `_next`-eignir, `favicon.ico` né API-rúturnar þrjár. Undanskilinn flötur er
 * flötur sem lifir af lokun.
 */
export function middleware() {
  return new Response("Not found", {
    status: 404,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      // Ekkert hér má rata í leitarvélar né skyndiminni. Slóðirnar voru
      // opnar og ómerktar fram að þessu, svo merkingin er sett á sjálft
      // 404-svarið frekar en að treysta á robots.txt sem var aldrei til.
      "x-robots-tag": "noindex, nofollow",
      "cache-control": "no-store",
    },
  });
}

export const config = {
  matcher: ["/:path*"],
};
