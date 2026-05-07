# HMS dialogue email — draft

**Status**: draft, ready for Danni review + send
**Written**: 2026-05-07
**Recipient candidates**: `info@hms.is` (general inquiry); refine if Danni has a specific contact in mind (e.g., from the Áfangi 4.9 matsvæði-polygon engagement that's already underway)
**Re-frame**: this email is NOT "may we please have access" — it surfaces today's empirical finding (the public `/api/fasteignaskra/` endpoint was retired in HMS's recent rebuild) and offers HMS three concrete response options. Positions us as a respectful actor who has already done the diligent work and is asking HMS to choose how they want to formalize what already exists.

---

## Suggested subject line

`Spurning um aðgang að gögnum úr fasteignaskrá HMS — ný útgáfa hms.is`

(English alternative: `Question about programmatic access to HMS fasteignaskrá data following the recent hms.is rebuild`)

---

## Email body (Icelandic, professional register)

```
Komiðu sæll,

Ég heiti Daniel og rek vefinn verdmat.is, óháðan vettvang sem býr til
verðmat á íbúðarhúsnæði byggt á opinberum þinglýstum kaupsamningum og
AI-líkönum kvarðaðum á raunverulegum sölum. Vettvangurinn er í rekstri
á https://verdmat-is.vercel.app og hefur verið opinber síðan apríl 2026.

Ég er að senda þér fyrirspurn varðandi aðgang að gögnum úr
fasteignaskrá HMS, og ég vil byrja á því að gera grein fyrir
nákvæmlega hvernig staðan er, því það er nokkuð mikilvægt samhengi.

Fram að nýlegu hafði hms.is/fasteignaskra opnað JSON API á slóðinni
/api/fasteignaskra/{fastanúmer} sem skilaði gögnum um eina fasteign í
einu (heimilisfang, fasteignamat, brunabótamat, stærð, byggingarár,
notkunarflokkur, o.s.frv.). Ég hafði byggt smá Python-tól sem notaði
þessi endapunkta til að sækja sérstök fastanúmer þegar þurfti, með
2-sekúndna seinkun á milli fyrirspurna og virðingu fyrir þvílíkum
álagsmörkum sem talið var hæfilegt fyrir opinbera þjónustu.

Þann 7. maí 2026 prófaði ég endapunktinn aftur og fékk HTTP 404 á
fimm þekktum fastanúmerum (þ.m.t. 2000042 sem var prófunardæmi í
upprunalegu verkefnislýsingunni). Það er ljóst af svartímum, X-Vercel
og X-Powered-By: Next.js hausunum að hms.is hefur verið
endurbyggður á nýjan tæknistakk (Next.js + Vercel + Prismic CMS) og
að gamli /api/fasteignaskra/ endapunkturinn var fjarlægður í þeirri
endurbyggingu. Þetta er innan ykkar fullrar heimildar — opinber API
án formlegs samnings er ávallt háður fyrirvarnarlausri breytingu.

Því er ég að rita ykkur núna til að spyrja: hvernig vill HMS standa
að aðgengi að fasteignaskrárgögnum áfram?

Ég sé þrjár mögulegar leiðir og er sveigjanlegur með hverja þeirra:

(a) HMS staðfestir nýja opinbera endapunkt sem leysir gamla af. Ef
    þannig endapunktur er til (t.d. í tengslum við endurbyggða
    fasteignaskrá-síðuna) þá þyrfti aðeins að fá slóðina og
    leiðbeiningar um sanngjörn álagsmörk. Mun hagstæðasta leiðin fyrir
    báða aðila.

(b) Formlegur API-aðgangssamningur. Skráð notkun, þekkt UA-hausan
    með auðkenni verdmat.is, samkomulag um álagsmörk og
    uppfærslucadence. Ég get sent inn formlega beiðni eftir kerfi
    HMS ef þið hafið slíkt fyrirkomulag.

(c) Reglulegur bulk-export. Annaðhvort dagleg eða mánaðarleg
    útflutningsskrá sem inniheldur fasteignaskrá í heild eða
    breytingar frá síðustu útgáfu. Mun léttari á álagi á ykkar kerfi
    en (a) eða (b).

Ég vil einnig nefna að þetta tengist annarri umræðu sem ég hef verið
að undirbúa við ykkur — beiðni um afhendingu matsvæði-fjölhornaskrár
(matsvæði polygon shapefile) til notkunar í markaðsgreiningardashboard
á verdmat.is/markadur. Sú beiðni er enn ekki formlega send, en ef
þið vildi taka báðar fyrirspurnirnar saman í einum umræðu þá er ég
til í það.

Ég vil leggja áherslu á nokkur atriði:

- Verdmat.is er ekki samkeppnisaðili HMS; við byggjum á sömu
  opinberu gögnunum og bjóðum fram íslenskum almenningi annars konar
  birtingaraðferð (verðmat með óvissubilum, fjölvarpsbreytingum,
  o.s.frv.). Aðgangur okkar að ykkar gögnum er það sem gerir kleift
  að gera þetta vandaða.
- Við erum tilbúin að virða þau álagsmörk sem þið setjið og að
  auðkenna okkur skýrt í UA-hausunum.
- Ef formlegur samningur er nauðsynlegur er ég til í að skrifa undir
  hver þau skilyrði sem þið setjið — það er hagsmunir okkar að halda
  góðum samskiptum við ykkur, ekki að fara í kringum þau.
- Þetta er ekki tímakröft fyrirspurn. Ég get beðið í 4-12 vikur
  eftir formlegri svari og hef nóg af öðru að gera á meðan.

Ef það er einfaldara í umræðu, get ég líka komið í síma eða heimsótt
ykkur ef þið kjósið. Ég er staðsettur á Reykjavíkursvæðinu.

Þakka fyrir tíma þinn,

Daniel Þór Magnússon
verdmat.is
[Danni's email/phone goes here]
```

---

## English version (for HMS staff who prefer it, or for record)

```
Dear HMS team,

I am writing about access to HMS fasteignaskrá data following your
recent hms.is rebuild.

My name is Daniel, and I run verdmat.is, an independent residential
valuation platform that produces estimates from public deeds-registry
data and AI models calibrated on actual sales. The platform has been
publicly available at https://verdmat-is.vercel.app since April 2026.

Until recently, hms.is/fasteignaskra exposed a JSON API at
/api/fasteignaskra/{fasteignanúmer} which returned per-property data
(address, fasteignamat, fire-insurance valuation, size, year built,
use-classification, and related fields). I built a small Python tool
that used this endpoint to fetch specific fasteignanúmer when needed,
with a 2-second delay between requests and respect for what seemed
like reasonable load limits for a public service.

On 7 May 2026 I tested the endpoint again and received HTTP 404 on
five known-good fasteignanúmer (including 2000042, which was the
reference example in the original project description). The response
headers (Server: Vercel, X-Powered-By: Next.js, X-Matched-Path:
/is/[...uid]) make it clear that hms.is has been rebuilt on a new
technical stack (Next.js + Vercel + Prismic CMS) and that the old
/api/fasteignaskra/ endpoint was removed in that rebuild. That is
fully within your authority — a public API without a formal agreement
is always subject to change without notice.

So I'm writing to ask: how does HMS want to handle ongoing access to
fasteignaskrá data?

I see three possible paths and I am flexible on which works for you:

(a) HMS confirms a new public endpoint replacing the old one. If
    such an endpoint exists (e.g., in connection with the rebuilt
    fasteignaskrá page) it would be enough to receive the URL and
    guidance on reasonable load limits. By far the easiest for both
    parties.

(b) Formal API access agreement. Registered usage, identifying
    User-Agent header, agreed load limits and update cadence. I can
    submit a formal request via HMS's standard intake process if you
    have one.

(c) Periodic bulk export. Either daily or monthly export file
    containing fasteignaskrá in full or as changes since the previous
    export. Much lighter on your infrastructure than (a) or (b).

I'd also note that this connects to a separate engagement I have been
preparing — a request for the matsvæði polygon shapefile for use in
a market-analysis dashboard on verdmat.is/markadur. That request has
not yet been formally submitted, but if you would prefer to handle
both inquiries in a single conversation, I'm happy to do so.

A few points I want to emphasize:

- verdmat.is is not a competitor to HMS; we build on the same public
  data and present it to the Icelandic public in a different form
  (valuations with uncertainty intervals, market-trend visualization,
  and so on). Access to your data is what makes this work properly.
- We are prepared to respect whatever load limits you set and to
  identify ourselves clearly in our User-Agent headers.
- If a formal agreement is required, I am ready to sign whatever
  terms you set — it is in our interest to maintain a good
  relationship with HMS, not to circumvent it.
- This is not time-pressured. I can wait 4-12 weeks for a formal
  response and have plenty of other work to do in the meantime.

If a phone call or in-person meeting would be more efficient, I'm
available — I'm based in the Reykjavík area.

Thank you for your time,

Daniel Þór Magnússon
verdmat.is
[Danni's email/phone goes here]
```

---

## Notes for Danni before sending

- Replace `[Danni's email/phone goes here]` with actual contact info.
- The Icelandic version is the primary; the English translation is provided in case the receiving HMS staff member prefers it (some older HMS staff may not work in Icelandic technical-register fluently, though most do).
- The matsvæði-polygon mention bundles the Áfangi 4.9 engagement that's been in PLANNING_BACKLOG since 2026-04-22. If you would rather keep them separate (single concern per email is sometimes cleaner), drop that paragraph.
- The email leans into the framing that HMS retired the API as their decision, and asks them to choose how to handle going forward. This is a much stronger position than "may we please have access" because it doesn't suggest we need permission to do something we haven't been doing — it suggests we already had a respectful working relationship with their public API and are now asking how to continue.
- Tone is professional without being obsequious. The empirical-fact citation (HTTP 404, X-Powered-By header) demonstrates we did the work properly before reaching out, which builds credibility. The 4-12 week patience clause makes clear we're not pressuring them, which removes any incentive to brush us off.
- Do NOT mention the existing scraper output (124,835 rows) or the SQLite databases. Even if the relationship was always with the public API, surfacing the existence of bulk historical data could complicate the conversation unnecessarily. The email is forward-looking only.
- Do NOT mention the parallel evalue.is scrape track. That is independent of HMS and not their concern.

---

## What this draft does NOT include

- Any time-bound demand or escalation language
- Any mention of regulatory frameworks (GDPR, Public Records Act, etc.) that might be read as adversarial
- Any mention of competing services (e-value.is, fastinn.is) — keeps the conversation about HMS-and-verdmat
- Any code samples or technical depth beyond what's needed to demonstrate the empirical observation about the rebuilt site
- Promises about specific volume or revenue ("we have 10,000 users", "we make X per year") — those would shift the conversation toward commercial-licensing territory, which we want to avoid for the public-data use case

The email is intentionally short for a 4-12 week dialogue ramp; depth comes in the follow-up exchange if HMS engages.
