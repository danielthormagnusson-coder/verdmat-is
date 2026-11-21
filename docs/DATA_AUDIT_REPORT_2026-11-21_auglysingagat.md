# DATA AUDIT — auglýsingagat 10.07.2025–08.06.2026 (2026-11-21, cc362)

Ný úttekt með dagsetningarviðskeyti (DATA_AUDIT_REPORT.md er skyndimynd frá 18.04.2026). Heimild: `D:\_audit\cc362_solusaga\SKIL_CC362.md`.

## Auglýsingagat 10.07.2025 – 08.06.2026 (cc362, mælt 21.11.2026)


**Töflur og jaðrar:**

| hlið | tafla | síðasta / fyrsta röð |
|---|---|---|
| eldri skrá (evalue, frosin) | `scraper.auglysinga_atburdir` (464.866 raðir, `byggt_ur = listings_v2.pkl@2026-04-15`); frumgögn `D:\Gagnapakkar\fasteignir*.db` (16.04.2026) | Eðlilegt magn til **09.07.2025** (106 auglýsingar þann dag, 564–581 á dag 01.–03.07). **10.07.2025: 37**, síðan 0–7 á dag. Strjálar raðir ná til 15.04.2026 13:00 UTC (7.861 eftir 15.07.2025, þar af um 3.600 í 03–04.2026) |
| lifandi mbl | `scraper.listings` (source = mbl), `parsed_mbl.db` / `raw_mbl.db` | Fyrsta sókn **09.06.2026 16:44 UTC** (`raw_fetches`, `parsed_mbl_sale.fetched_at`). Fyrsta lífsferilssópun 03.07.2026 06:40 UTC. `discovered_at` er skráður frá 04.07.2026 |
| auglýsingar stofnaðar í gatinu | `scraper.listings` / `parsed_mbl_sale.created` | aðeins auglýsingar sem lifðu fram í 06.2026: 7.626 auðkenni stofnuð 07.2025–05.2026 í `parsed_mbl_sale` (123 í 07.2025 upp í 3.285 í 05.2026). Auglýsing sem hvarf fyrir 09.06.2026 er ekki til |

**Magn á móti þinglýstum sölum** (auglýsingar á sölu í sama mánuði): 2024: 4,5–10,9 · **07.2025: 1,71** · 08.2025–02.2026: 0,46–0,91 · 03–04.2026: 1,8–3,2 · 05.2026: 2,96 · frá 06.2026: 11,6–26.

**Hvað það snertir:**
- Söluferli sem hefjast 17.06.2025–15.06.2026 (gatið ± N = 14 d) telja upphafið óvíst (`upphaf_viss = false`). Það eru 14.290 ferli á 11.222 eignum.
- **Af 8.554 eignum á sölu 21.11.2026 eru 4.097 (47,9 %) með óvíst upphaf** (íbúðir 3.394 af 7.204, 47,1 %). Þær fá „Minnst N dagar á sölu“ / „frá a.m.k. DD.MM.ÁÁÁÁ“. Hlutfallið fellur af sjálfu sér eftir því sem ferlin endurnýjast.
- cc339: pörun sölu og auglýsingar 27,3 % fyrir kaupsamninga 08.2025–05.2026 (66,6 % fyrir, 74,7 % eftir). Dagar á sölu í gatinu eru tvöfaldir vegna úrtaksskekkju.
- `in_scrape_gap` í Áfanga 1 (§11 hér að ofan) merkti sölur ≥ 2025-07-01. cc362 mælir sama gat á auglýsingahliðinni og finnur lok þess: 08.06.2026 / 09.06.2026.

**Diskleit 21.11.2026 (aðeins lestur):** engin eldri skafgögn frá gatinu fundust (sjá SKIL_CC362, viðbót).
