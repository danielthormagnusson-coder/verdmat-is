# GEN-FERLI mánaðarskýrslu Fable — v1 (skjalfest 2026-07-15, cc5)

Endurnýtanlegt prompt/gátlisti. Næsti mánuður er **handvirk trigger-keyrsla á þessu ferli, ekki endursmíði**. Sjálfvirkni og UI-tenging eru sér-ákvarðanir.

## Trigger-prompt (gefið nýrri lotu)

> Keyrðu GEN_FERLI_v1 fyrir mánaðarskýrslu Fable, tímabil [MÁNUÐUR ÁR]. Fylgdu
> docs/fable_skyrslur/GEN_FERLI_v1.md skref fyrir skref. Micro-HALT á beinagrind,
> HALT á fullbúinni skýrslu. Engin skrif í prod, engin DB-skemabreyting, commit
> aðeins eftir go.

## Fasi 0 — rammi

- [ ] Klukka tvíhliða (staðartími + UTC); skjalfestu afmörkun tímabils (heill nýliðinn mánuður + það sem af er yfirstandandi).
- [ ] Samhliða-tékk: hvaða aðrar lotur keyra? Þessi lota les DB read-only og skrifar aðeins nýjar skrár í app-repo (`docs/fable_skyrslur/`, `heimildasafn/`).

## Fasi 1 — heimildaöflun (og VARANLEG vistun)

Safnreglur (fyrirmæli eiganda, 2026-07-15):
1. Safnskipulag `heimildasafn/[heimild]/[ártal]/`; skráarheiti `[utgafudags]_[heiti]_sott[dags].[ext]`.
2. PDF/CSV/XLSX vistast HRÁ (bætin). API-svör sem hrá JSON. Fréttir: ALDREI efnið — metadata-JSON (fyrirsögn/miðill/dags/hlekkur).
3. MANIFEST.json append-only með md5; endursókn = ný færsla aðeins ef md5 breytist. (Skripta-sniðmát: build_manifest.py mynstrið — walk, md5, URL-tafla.)
4. `.gitignore`: `heimildasafn/**` með `!MANIFEST.json` og `!frettir/**` undanþágum (þegar frágengið).
5. Backup: `app_heimildasafn` include-færslan í `scripts/backup_paths.json` (frágengin 2026-07-15) — sannreyna í fyrstu keyrslu mánaðar að nýjar skrár skili sér.

Heimildalisti (fastir liðir):
- [ ] **HMS**: mánaðarskýrsla (hms.is/skyrslur/manadarskyrsla-[mán]-[ár] — full vefútgáfa er efnismesta heimildin + Excel-fylgigögn), kaupvísitala.csv + leiguvísitala.csv (OCI-slóðir í MANIFEST — CSV-serían er frumheimild vísitölugilda, ekki fréttirnar), fasteignamat ef júní.
- [ ] **Hagstofan**: VNV-frétt mánaðarins (útg. ~26. hvers mánaðar).
- [ ] **Seðlabankinn**: forsíðan (meginvextir + næsta vaxtaákvörðun — vélrænt læsileg), yfirlýsing PSN + Peningamál ef vaxtaákvörðun var á tímabilinu (PDF hrá).
- [ ] **Bankar**: landsbankinn.is/umraedan/efnahagsmal (listasíða svarar WebFetch), Íslandsbanki (greinar svara; listasíður eru JS — leita), Arion (JS-þung — leita; gat ef ekkert finnst).
- [ ] **Fréttir**: leit á tímabilinu; metadata-JSON í frettir/[ártal]/.

### Gildrur (lærdómur cc5, 2026-07-15)

| Gildra | Vörn |
|---|---|
| **Ártalagildran** — leitarvélar skila gömlum greinum (2019/2022/2024) sem „nýjustu“; algengasti villuflokkurinn | Opna HVERJA heimild og staðfesta útgáfudag ÁÐUR en tala er notuð; henda röngum árum úr safni |
| hms.is er á bak við Cloudflare WAF | `curl_cffi` með `impersonate="chrome120"`; ALDREI Invoke-WebRequest/WebFetch á hms.is |
| PX-API Hagstofu svarar vélfyrirspurnum ekki (WAF) | VNV-frétt + HMS-CSV duga; skrá gat ef frumserían næst ekki |
| vb.is gefur 403 á WebFetch | curl_cffi virkar |
| JS-tómar síður (SÍ-viðburðir, Arion/ÍSB listar) | Athuga bætastærð (<10 KB skel = ónothæf); nota forsíðu SÍ í staðinn fyrir dagatal |
| Löng PDF hafa token-þak í fetch-i | Taka töflur/lykiltölur, ekki heildarskjöl; flagga það sem næst ekki |
| Start-Process + python = cp1252 kóðunarhrun | `$env:PYTHONIOENCODING="utf-8"` fyrir ræsingu |

## Fasi 2 — eigin gagnabanki (read-only)

Fastar fyrirspurnir (SQL-mynstur í VINNSLUGOGN_2026-06 og samtali cc5; Supabase MCP execute_sql):
- [ ] Ferskleiki: `max(thinglystdags)` í sales_history — verður að ná inn í skýrslumánuðinn.
- [ ] Velta: skýrslumánuður eftir árum (2021→) + yfirstandandi mánuður 1.–15. (alltaf með þinglýsingartafar-fyrirvara, enginn árssamanburður), síað **og** ósíað.
- [ ] Miðgildi kr/m²: skýrslumánuður eftir árum + 12-mán svæðatafla (n≥100, **TRIM(sveitarfelag)** — tvískráningargildran).
- [ ] Framboð: virkar sölu-/leiguauglýsingar (category/tenure); athuga hvort lifecycle-hreinsanir séu í gangi → fyrirvari FYLGIR tölunni í alla kafla.
- [ ] Ásett/verðmat: percentílar eftir svæðum, hlutfall síað [0,3;3,0]; hlutlaus staðreynd, engin tækifæris-orðræða.
- [ ] Leiga: miðgildi ásetts verðs + kr/m² (nefnari: ásett ≠ samningar).
- [ ] Krossskoðun við opinberu tölurnar; frávik eru EFNI (nefnaramunur skýrður), ekki falin.
- [ ] Göt skráð, ekki fyllt (sölutími/verðbreytingar þar til gögn batna).
- [ ] Niðurstöður vistaðar: `docs/fable_skyrslur/VINNSLUGOGN_[tímabil]_[UTC].json`.

## Fasi 3 — beinagrind (micro-HALT)

- [ ] Efnisyfirlit (10 kaflar + viðaukar, sjá FASTEIGNASKYRSLA_2026-06 sem sniðmát) + einn fullskrifaður dæmikafli → relay → **bíða go**.

## Fasi 4 — fullvinnsla (eftir go)

- [ ] **Dagsetningasamræmistékk**: hver útgáfudagur í texta borinn saman við MANIFEST/frumskrár (skerping Danna 1b — ártalagildran er villuflokkurinn).
- [ ] Ef vísitala mánaðarins er óbirt (birtist ~3. þriðjudag næsta mánaðar): skýrslan hvílir á nýjasta birta gildi og **efsta lína samantektar segir það berum orðum** (skerping 1a).
- [ ] Framboðs-/gagnafyrirvarar fylgja tölunum í ALLA kafla þar sem þær birtast, líka lykiltölukassa (skerping 1c).
- [ ] Skrifa: `FASTEIGNASKYRSLA_[tímabil]_[UTC].md` + `HEIMILDASKRA_[tímabil]_[UTC].md` (hver tala → safnslóð + sótt-dags).
- [ ] Gröf sem gagnasett+gerð í viðauka B (engin myndvinnsla í þessari lotu).
- [ ] Tónn: hlutlaus greining; spár alltaf eignaðar heimild; ENGIN verðráðgjöf.
- [ ] **HALT**: skýrsla + ferli relayað; commit aðeins eftir go (explicit paths, aldrei `git add .`).

## Föst commit-mengun eftir go

`docs/fable_skyrslur/*` (skýrsla, heimildaskrá, vinnslugögn, gen-ferli) + `heimildasafn/MANIFEST.json` + `heimildasafn/frettir/**` + `.gitignore`/`backup_paths.json` ef breytt. Hrá safngögn fara ALDREI í git.
