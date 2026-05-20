Secondary keys:
- `faerslunumer` — sale transaction PK (one fastnum → many sales). Joins to kaupskra.csv FAERSLUNUMER for ONOTHAEFUR_SAMNINGUR, TEGUND.
- `augl_id` — listing PK (one fastnum → many listings).

Derived join:
- `pairs_v1.pkl` matches augl_id ↔ faerslunumer within a fastnum (which listing led to which sale, via temporal + price logic). The only non-native join.

**fastnum lifecycle**: fastnum is not perfectly stable. Lot mergers / renumbering can deregister a fastnum (see 97 ghosts soft-flagged in Phase D2, deregistered=true). Future work may require fastnum aliasing (old → new).

---

## The Supabase-canonical decision (HMS metadata)

**Decision**: Supabase `properties` is canonical for HMS property metadata (fasteignamat, stærð, byggingarár, byggingarstig, brunabótamat, matseiningar, lhlmat, etc.).

**Consequence**: `properties_v2.pkl` is now a DERIVED cache. On each training cycle, `rebuild_training_data.py` must export the HMS slice from Supabase → local parquet before building the training matrix, not read the stale local pickle.

**Tradeoffs accepted**:
- Training depends on Supabase reachability + an export step. Mitigation: export caches locally, so a temporary outage does not block training if a recent export exists.
- Indirect round-trip (scrape → Supabase → export → train) but guarantees training uses exactly the data the serving layer shows.

**Unblocks**: iter5 — once rebuild pulls HMS from Supabase, training has access to brunabótamat / byggingarstig non-circular features.

---

## Open follow-up (in PLANNING_BACKLOG)

- **rebuild_training_data.py HMS export step**: export HMS columns from Supabase → local parquet at start of training cycle. ~1 day. Non-blocking (iter4 does not use new HMS columns). Linked to iter5.
