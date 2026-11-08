-- cc331 B5 (GO Danna 08.11.2026): fasteignasala hverrar íbúðar sem er á sölu NÚNA, svo /nybyggingar geti sagt
-- „Söluaðilar núna" með sama mengi og „á sölu" (n_auglyst). Skrifað af scripts/cc224_nybygging_verkefni.py.
--   augl_stofa_lykill, augl_stofa: venjuleg eining á sölu (stada a_solu, ekki óskipt) — stofa nýjustu virku auglýsingarinnar
--   augl_stofur: óskipt fastanúmer — [{lykill, nafn, n}] yfir virkar auglýsingar þess, Σ n ≤ n_auglyst
-- Nullable án sjálfgefins gildis: aðeins lýsigögn breytast, enginn endurritun töflu. Töflu-GRANT (SELECT til anon,
-- authenticated) og RLS-stefna nybygging_einingar_les ná yfir nýja dálka; engin ný heimild.
BEGIN;
SET TRANSACTION READ WRITE;
ALTER TABLE semantic.nybygging_einingar
  ADD COLUMN augl_stofa_lykill text,
  ADD COLUMN augl_stofa text,
  ADD COLUMN augl_stofur jsonb;
ALTER TABLE semantic.nybygging_einingar
  ADD CONSTRAINT nybygging_einingar_augl_stofur_chk CHECK (augl_stofur IS NULL OR jsonb_typeof(augl_stofur) = 'array') NOT VALID;
COMMENT ON COLUMN semantic.nybygging_einingar.augl_stofa_lykill IS 'cc331: lykill fasteignasölu nýjustu virku söluauglýsingar (eining á sölu, ekki óskipt)';
COMMENT ON COLUMN semantic.nybygging_einingar.augl_stofa IS 'cc331: birtingarheiti sömu fasteignasölu';
COMMENT ON COLUMN semantic.nybygging_einingar.augl_stofur IS 'cc331: óskipt fastanúmer — [{lykill, nafn, n}] virkar auglýsingar, sum n <= n_auglyst';
COMMIT;
