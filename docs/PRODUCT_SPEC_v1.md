# PRODUCT_SPEC v1

**Staða:** rýnt og samþykkt af eiganda 2026-08-03. Skjalið er HÖNNUN, ekki staðreyndaskrá —
hver tala sem hér er nefnd vísar á audit-skjal eða DB og skal sannreynd þaðan áður en hún er
notuð. Breytingar á þessu skjali fylgja append-only reglunni héðan í frá.

---

## 1. Varan í einni málsgrein

verdmat.ai er verðmats- og markaðsgreiningarkerfi fyrir íslenskar íbúðareignir, byggt á
þinglýstum kaupsamningum og heildarskröpun auglýsingamarkaðarins. Sölupunkturinn er heiðarleg
óvissa: hver tala ber mælingu, bil, þrep og flokk — og það sem ekki stenst nefnara-skoðun
birtist sem stöðumerki, ekki tala. Neitunin (þrep 5) er banka-eiginleiki, ekki veikleiki.

## 2. Aðgangsstigin þrjú

**Lag 1 — óskráðir:** grunnmat (punktmat + 80/95% bil, þrep, flokkur), leit, markaðssíðan,
„Á sölu"-flöturinn. Ekkert notandainntak sem varðar mat. Tilgangur: dreifing og trúverðugleiki.

**Lag 2 — innskráðir borgandi + fasteignasalar:** allt í lagi 1, auk leiðréttingarlagsins
(leiðrétt viðmið m/waterfall og provenance per línu), tveggja-talna leiguflatarins (§5),
kafa-dýpra reiknivélarinnar (§6), HMS-staðreyndaflatarins (§7), vistaðra leita (þegar G1 opnar)
og PDF-útskrifta.

**Lag 3 — fasteignasalar einir:** persónulegt mat fasteignasala (per-notanda RLS, sannað á
prod), söluyfirlits-smiðjan (§8), og merkingar sem bera nafn stofunnar. Aðgreiningin frá lagi 2
er ábyrgðarlagið: fasteignasali skrifar undir sitt mat, kerfið skilar sínu ósnertu við hliðina.

**Ófrávíkjanleg regla allra laga:** grunnmatið er deterministic og ósnertanlegt; ekkert samtal,
inntak eða áskrift breytir því. Notandainntak lifir í aðskildum lögum OFAN á matið, hvert með
sýnilegri forsendu. Þrep og flokkur sitja á grunnmati einu.

## 3. Leiðréttingarlagið

Þriggja talna sýnin: grunnmat (ósnert) → leiðrétt viðmið (mældir nettó-stuðlar, log-samhverft
þak ×1,15 í hvora átt — aldrei orðað „±15%") → persónulegt mat sala. Continue-hliðin fjögur
(lib/leidretting.js) og tvíflokkurinn ástand/misræmi standa eins og útfært er á prod.
Efnisskrá stuðla ber fimm stöður og hver birtanlegur stuðull vísar í mælingu (cc38/cc40/cc41);
einkalóðar-stuðullinn er í sóttkví þar til mæling skýrir hann. Condition-upplýsingar birtast
sem merki, ALDREI sem verðleiðrétting (iter5-dómurinn). Bil hliðrast aldrei með laginu.

Eigindi koma úr tveimur lindum og bera provenance hvor: paraðar sölur (söluyfirlit) og virkar
auglýsingar (extraction-brúin). JÁ-bias-vörnin heldur í báðum: CHECK í DB hafnar neikvæðu frá
extraction-lind en hleypir notanda/söluyfirliti.

**Lind-uppfærsla á dagskrá:** ÍslandsDEM 2×2m gefur sjávarútsýni/suðurátt deterministic með
100% þekju í stað JÁ-bias extraction.

## 4. Söluflöturinn

„Á sölu"-kortið les næturskröpunina beint: ásett verð birtist sem samhengislína við hlið
grunnmats („Ásett verð er X, grunnmat Y") — engin prósenta, engin röðun, ekkert
vanmats-orðalag. Auglýsingatexti á sér EITT heimili (söluyfirlits-flöturinn), merktan lindinni:
virk auglýsing vinnur, pöruð sala annars. Þetta er ask-to-sale sagan sem enginn annar sýnir og
verður mælanleg söluvara þegar ask-to-sale-gap módelið bætist við.

## 5. Leigu-framsetningin

Tvær tölur á öllum leiguflötum, báðar merktar:

- **A. Áætluð auglýst leiga** = samningsmat × mælt ask-álag (heimildin orðrétt: „leiguverðsjá
  HMS maí 2026"-mælingin).
- **B. Áætluð samningsleiga** = módelið sjálft (rent_v1_nan, aðaltalan).

Skýringartextinn orðast AÐEINS á mældu rótunum: ask-álag og birgða-elding verðsjárinnar.
Skýring um félagslega mengun er HÖFNUÐ — krossmælingin mældi verðsjána ómengaða. Notandinn sem
ber saman við auglýsingar les A; bankinn sem ber saman við þinglýsingar les B.

## 6. Kafa-dýpra reiknivélin (lag 2)

Hnappur á eignasíðu opnar vinnuflöt: yield út frá matinu (breytanleg leigutala m/sýnilegu
fráviki frá módelspá), hefðbundinn rekstrarkostnaður (sjálfgefin gildi m/heimild, öll
breytanleg), lán (fjárhæð + vextir) — og út kemur rekstraráætlun m/yield fyrir og eftir kostnað.
Reglurnar: hver forsenda notandans er sýnileg og merkt sem hans; grunnmat og leigumat standa
ósnert sem viðmið; engin röðun eigna eftir yield nokkurs staðar. Þetta færir síðuna úr
uppflettingu í vinnutæki — kjarni áskriftarraksins.

## 7. HMS-staðreyndaflöturinn

Hnappur við hlið Söluyfirlits sem sýnir HMS-skráninguna sem við eigum sjálf: tegund, gerð,
stærðir, byggingarár, matseiningar. **Regla:** stangist HMS á við söluyfirlitið poppar
misræmið upp og notandinn velur lind — kerfið þegir ekki og velur ekki fyrir hann. Árekstrarnir
eru sannreyndir, ekki tilgátulegir: HMS-röðin ber sjálf bæði svörin á fjölda eigna
(notkunar-flötur vs matseiningar-gerð), mælt í cc76-úttektinni.

## 8. Söluyfirlits-smiðja fasteignasala (lag 3)

Tvennt ALGERLEGA AÐSKILIÐ:

- **(a) Heilt söluyfirlit** skv. stöðluðu formi sem eigandi leggur til.
- **(b) Lýsing ein og sér** — ekkert annað.

Viðmiðunarefnið er þegar til: lýsingar fylgja auglýsingum í gagnasafninu og nýtast bæði sem
þjálfunar- og viðmiðunarefni. Smiðjan skrifar aldrei tölur úr matinu inn í söluyfirlit án þess
að þær beri sömu merkingar og á síðunni (þrep, flokkur, bil). Sendingarferlið á fasteignasala
er á hendi eiganda og telst ekki með í umfangi vörunnar.

## 9. Lánasafns-B2B

Eina B2B-leiðin sem er sönnuð í kóða: frumgerðin frá 05.06 í trunadargogn/ (deilist aldrei án
bankaheimildar). Spec-staðan: lánasafns-skimun gegn grunnmati + þrepakerfi, afhent sem innra
tól — ekki opinber flötur. Verðlagning og samningsform eru eigandaákvarðanir; skjalið bókar
aðeins að tæknilega frumgerðin er til og að þrep-5-neitunin er þar söluvara.

## 10. Greiðslugátt (verkefni, ekki niðurstaða)

Valkostir sem greinast: innlend kortagátt, Stripe með ISK-uppgjöri, reikningsleið fyrir stofur.
Greiningin er óunnin — bókast sem verkefni með þremur spurningum: (a) ISK-uppgjör og VSK-meðferð
áskrifta, (b) kortageymslu-áhætta (PCI út með hosted checkout), (c) stofu-reikningar vs kort
einstaklinga. Engin niðurstaða valin hér.

## 11. Kostnaðarvarnir

Þrjú þök, öll með mælingu og viðvörun áður en þjónusta brotnar: Vercel (spend-limit + pause
virk; myndakostnaður skorinn með breiddaþaki, árs-TTL, myndaþaki á söluyfirliti og robots.txt —
R2-myndaspegillinn er rótarfixið og liggur í biðröð), Anthropic API (extraction-kvóti per nótt
í keðju; mánaðarþak bókast), R2/backup (wrapper-logg vaktað). Ops-síðan ber alla þrjá fletina.

Lærdómur sem festist hér: kostnaðarvöxtur getur komið frá vélrænni umferð sem enginn notandi býr
til. Mælikvarði sem ber ekki nefnara (beiðnir án þess að vita hvaðan) dugar ekki til varnar.

## 12. Ops og aðgangsstjórnun

Vöktunarvélin + /ops (læst á netfang eiganda, rautt-fyrst, 30-mín gulnun) — vaktar-próbinn er
bráðabirgðalag og AFSKRÁIST þegar vélin tekur við; tvö kerfi lifa aldrei samhliða.
**Aðgangsstjórnunarsíða** er sjálfstæður flötur við hlið /ops: stofna og eyða aðgöngum, sjá
notkun per notanda, loka aðgangi án handavinnu í DB. Hlutverkalagið er þegar til í DB; viðmótið
vantar.

## 13. Leitar-vaxtarkaflinn

Fasar 1–2 af valseðlinum eru live. Eftir standa: extraction-gáttin, tags, bílskúrs-sía, a-síur,
vistuð leit (domain-verification er hliðið), POI, verð-lækkað — og **kortaleit**, sem er
innkomuhátturinn sem notendur koma með frá mbl. Vaxtarreglan óbreytt: hver /leit-breyting ber
TTFB-vörn ×9.

## 14. Fastinn-samanburður (opið verkefni)

Kerfisbundin úttekt á fastinn.is og bókun á því sem vantar hjá okkur — sérstaklega opinber
gjöld (fasteignaskattur, vatnsgjald, fráveitugjald, lóðarleiga, áætluð heildargjöld/mán),
umferðarhávaði (kortlagning Vegagerðarinnar 2022), þjónustustig og viðhaldsskuld. Fastinn er
ÓNÝTUR sem krossheimild (speglar mbl-auðkenni) en er hreinn eiginleika-samanburður: það sem
hann sýnir og við ekki er eiginleikaskuld, ekki gagnaskuld.

## 15. Opnar ákvarðanir eiganda

1. Verðlagning laga 2 og 3.
2. Greiðslugáttar-greiningin (§10) — hver keyrir hana og hvenær.
3. Staðlaða söluyfirlits-formið (§8) — eigandi leggur til.
4. Beta-merkingar leiguflatarins: standa þær gegnum sendingu eða víkja á söluhliðinni?
