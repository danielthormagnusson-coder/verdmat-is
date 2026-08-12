# cc135 — afrit af lotu-skriftunum (leigu-þrepin á reglu R)

**Þetta er AFRIT, ekki frumritið.** Frumritin lifa í precompute-repoinu og eru
útgáfustýrð þar frá cc138:

| Skrá | Frumrit | Hlutverk |
|---|---|---|
| `cc135_freeze.py` | `verdmat-is-precompute@d5a3175` | Snapshot `valuation_tiers_rent_pre_cc135` + RLS default-deny + rollback-SQL á disk FYRIR aðgerð. Neitar að yfirskrifa snapshot sem er til. |
| `cc135_forsendur.py` | sama | READ-ONLY forsendumæling: lindin, frosna þéttleika-merkingin, segment-ásinn. Hólfun S0/S1/S2. |
| `cc135_parity.py` | sama | READ-ONLY parity + kohort + skammtasvörun. |
| `cc135_flip.py` | sama | Atómískt `TRUNCATE`+`INSERT` flipp staging→live. Krefst `--go`. |

Byggjarinn sjálfur (`build_rent_tiers.py`, +103/−16) er EKKI afritaður hingað —
hann er lifandi skrá í precompute og afrit hér yrði þögult tvírit.

Afritið er til af einni ástæðu: skriftarnar urðu til í lotu-scratchpad og
`docs/fable_prep/prototypes/` er sá staður sem geymir slík verkfæri í app-repoinu
(sbr. `cc39/`). Ef þeim ber á milli **gildir precompute-frumritið**.

Heimild: `docs/fable_prep/audits/LEIGU_THREP_CC135_20260812.md`.
