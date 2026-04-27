"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { formatSegment, formatM2 } from "@/lib/format";

// Bug 4 + Search UX overhaul (2026-04-22):
//   * Two-tier pattern — address-row groups first (one per
//     heimilisfang × postnr), inline-expand to unit rows on click.
//   * 7-digit fastnum queries bypass grouping and resolve directly.
//   * Empty state surfaces the HMS-data-gap caveat copy.

const FASTNUM_PATTERN = /^\d{7}$/;

function UnitIcon({ code }) {
  return (
    <span
      aria-hidden
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: 2,
        background:
          code === "APT_BASEMENT"
            ? "var(--vm-cold)"
            : code === "APT_FLOOR" || code === "APT_STANDARD"
            ? "var(--vm-primary)"
            : code === "SFH_DETACHED"
            ? "var(--vm-accent)"
            : code === "ROW_HOUSE" || code === "SEMI_DETACHED"
            ? "var(--vm-success)"
            : "var(--vm-ink-faint)",
        marginRight: 8,
        flexShrink: 0,
      }}
    />
  );
}

export default function SearchAutocomplete() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [emptyState, setEmptyState] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);

  // expandedKey = `${heimilisfang}|${postnr}` of the currently-expanded row (or null).
  const [expandedKey, setExpandedKey] = useState(null);
  const [expandedUnits, setExpandedUnits] = useState([]);
  const [expandedLoading, setExpandedLoading] = useState(false);

  const wrapRef = useRef(null);

  useEffect(() => {
    const onClick = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  useEffect(() => {
    if (!q || q.trim().length < 2) {
      setResults([]);
      setEmptyState(false);
      return;
    }

    // Bug 9 + 10 fix (2026-04-27): a slow cold RPC (~5 s) for an earlier prefix
    // was overwriting the correct fast result for a longer, fresher prefix
    // (e.g. typing "viðjugerði" briefly returned 15 Viðarás rows from the
    // older "viðar..." request resolving last). Two-layer guard:
    //   1. AbortController so Supabase's fetch is cancelled when q changes.
    //   2. `cancelled` flag + term-still-current check before any setState,
    //      so even if abort doesn't take effect (older clients) we never
    //      apply stale results.
    let cancelled = false;
    const controller = new AbortController();
    const term = q.trim();

    const handle = setTimeout(async () => {
      if (cancelled) return;
      setLoading(true);
      setExpandedKey(null);
      setExpandedUnits([]);

      try {
        // Fastnum direct lookup (7-digit Icelandic fastnum).
        if (FASTNUM_PATTERN.test(term)) {
          const { data, error } = await supabase
            .from("properties")
            .select(
              "fastnum, heimilisfang, postnr, postheiti, tegund_raw, canonical_code, einflm",
            )
            .eq("fastnum", Number(term))
            .abortSignal(controller.signal)
            .maybeSingle();
          if (cancelled) return;
          if (error && error.name !== "AbortError") throw error;
          if (data) {
            setResults([
              {
                heimilisfang: data.heimilisfang,
                postnr: data.postnr,
                postheiti: data.postheiti,
                n_units: 1,
                anchor_fastnum: data.fastnum,
                tegund_summary:
                  data.tegund_raw || formatSegment(data.canonical_code),
                _prefetchedUnit: {
                  fastnum: data.fastnum,
                  tegund_raw: data.tegund_raw,
                  canonical_code: data.canonical_code,
                  einflm: data.einflm,
                },
              },
            ]);
            setEmptyState(false);
          } else {
            setResults([]);
            setEmptyState(true);
          }
          setLoading(false);
          setOpen(true);
          setActiveIdx(-1);
          return;
        }

        // Grouped address search via RPC.
        const { data, error } = await supabase
          .rpc("search_properties_grouped", { term })
          .abortSignal(controller.signal);
        if (cancelled) return;
        if (error && error.name !== "AbortError") throw error;
        const rows = (data || []).map((r) => ({
          ...r,
          sveitarfelag: r.sveitarfelag ? r.sveitarfelag.trim() : r.sveitarfelag,
          n_units: Number(r.n_units),
        }));
        setResults(rows);
        setEmptyState(rows.length === 0);
        setLoading(false);
        setOpen(true);
        setActiveIdx(-1);
      } catch (e) {
        if (cancelled || e?.name === "AbortError") return;
        console.error("[SearchAutocomplete] search failed", e);
        setResults([]);
        setEmptyState(true);
        setLoading(false);
      }
    }, 220);

    return () => {
      cancelled = true;
      controller.abort();
      clearTimeout(handle);
    };
  }, [q]);

  async function expand(row) {
    const key = `${row.heimilisfang}|${row.postnr}`;
    if (expandedKey === key) {
      setExpandedKey(null);
      setExpandedUnits([]);
      return;
    }
    setExpandedKey(key);
    setExpandedLoading(true);
    // unit_category ("0100", "0101", "0102", …) is the HMS merking for a unit
    // inside a multi-unit building. properties.merking isn't exported from the
    // precompute pipeline, so requesting it used to silently error out and
    // surface as "Engar einingar" in the dropdown (Bug 5, 2026-04-22).
    const { data, error } = await supabase
      .from("properties")
      .select(
        "fastnum, tegund_raw, canonical_code, unit_category, einflm",
      )
      .eq("heimilisfang", row.heimilisfang)
      .eq("postnr", row.postnr)
      .eq("is_residential", true);
    if (error) {
      console.error("[SearchAutocomplete] expand failed", error);
      setExpandedUnits([]);
      setExpandedLoading(false);
      return;
    }
    const units = (data || []).slice().sort((a, b) => {
      // Basement units first per spec §Þrep 2, then by einflm desc.
      const aBase = a.canonical_code === "APT_BASEMENT" ? 0 : 1;
      const bBase = b.canonical_code === "APT_BASEMENT" ? 0 : 1;
      if (aBase !== bBase) return aBase - bBase;
      return (Number(b.einflm) || 0) - (Number(a.einflm) || 0);
    });
    setExpandedUnits(units);
    setExpandedLoading(false);
  }

  function chooseAddress(row) {
    if (Number(row.n_units) <= 1) {
      setOpen(false);
      router.push(`/eign/${row.anchor_fastnum}`);
      return;
    }
    expand(row);
  }

  function chooseUnit(u) {
    setOpen(false);
    router.push(`/eign/${u.fastnum}`);
  }

  function onKey(e) {
    if (!open || results.length === 0) {
      if (e.key === "Enter" && FASTNUM_PATTERN.test(q.trim())) {
        router.push(`/eign/${q.trim()}`);
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const idx = activeIdx >= 0 ? activeIdx : 0;
      if (results[idx]) chooseAddress(results[idx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={wrapRef} style={{ position: "relative", width: "100%" }}>
      <div style={{ display: "flex", gap: "0.6rem" }}>
        <input
          className="vm-input"
          type="text"
          placeholder="Heimilisfang eða fastanúmer"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onKey}
          onFocus={() => q && setOpen(true)}
          autoComplete="off"
        />
        <button
          className="vm-btn"
          style={{ whiteSpace: "nowrap" }}
          onClick={() => {
            if (results[0]) chooseAddress(results[0]);
            else if (FASTNUM_PATTERN.test(q.trim()))
              router.push(`/eign/${q.trim()}`);
          }}
        >
          Fá verðmat
        </button>
      </div>

      {open && (loading || results.length > 0 || emptyState) && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            left: 0,
            right: 0,
            background: "var(--vm-surface-elevated)",
            border: "1px solid var(--vm-border-strong)",
            borderRadius: 8,
            boxShadow: "0 8px 28px rgba(19, 36, 59, 0.10)",
            zIndex: 20,
            overflow: "hidden",
          }}
        >
          {loading && (
            <div
              style={{
                padding: "0.85rem 1rem",
                color: "var(--vm-ink-faint)",
                fontSize: "0.9rem",
              }}
            >
              Leita...
            </div>
          )}

          {!loading && emptyState && (
            <div style={{ padding: "0.95rem 1.1rem" }}>
              <p
                style={{
                  margin: 0,
                  fontSize: "0.9rem",
                  color: "var(--vm-ink)",
                  lineHeight: 1.5,
                }}
              >
                Engin eign fannst. Eignin er kannski ekki í gagnasafninu okkar
                enn. Við byggjum á HMS fasteignaskrá sem vantar sumar nýjar
                eignir og nýbyggingar — við erum að byggja fyllra gagnasafn.
              </p>
              <a
                href="/um#gagnasafn"
                style={{
                  display: "inline-block",
                  marginTop: "0.45rem",
                  fontSize: "0.82rem",
                  color: "var(--vm-primary)",
                }}
              >
                Skoða aðferðafræði →
              </a>
            </div>
          )}

          {!loading &&
            !emptyState &&
            results.map((r, i) => {
              const key = `${r.heimilisfang}|${r.postnr}`;
              const isExpanded = expandedKey === key;
              const nUnits = Number(r.n_units);
              const isMulti = nUnits > 1;
              return (
                <div
                  key={key}
                  style={{
                    borderTop: i === 0 ? "none" : "1px solid var(--vm-border)",
                  }}
                >
                  <div
                    role="button"
                    tabIndex={0}
                    onMouseEnter={() => setActiveIdx(i)}
                    onClick={() => chooseAddress(r)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        chooseAddress(r);
                      }
                    }}
                    style={{
                      padding: "0.75rem 1rem",
                      cursor: "pointer",
                      background:
                        activeIdx === i ? "var(--vm-surface)" : "transparent",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "1rem",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontWeight: 500,
                          color: "var(--vm-ink)",
                          marginBottom: "0.15rem",
                        }}
                      >
                        {r.heimilisfang} · {r.postnr} {r.postheiti}
                        {isMulti && (
                          <span
                            style={{
                              marginLeft: "0.5rem",
                              fontSize: "0.85rem",
                              color: "var(--vm-ink-muted)",
                              fontWeight: 400,
                            }}
                          >
                            ({nUnits} íbúðir)
                          </span>
                        )}
                      </div>
                      <div
                        style={{
                          fontSize: "0.85rem",
                          color: "var(--vm-ink-muted)",
                        }}
                      >
                        {r.tegund_summary || "—"}
                        {r.sveitarfelag ? ` · ${r.sveitarfelag}` : ""}
                      </div>
                    </div>
                    <div
                      aria-hidden
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--vm-ink-faint)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {isMulti ? (isExpanded ? "▾" : "▸") : "→"}
                    </div>
                  </div>

                  {isExpanded && (
                    <div
                      style={{
                        padding: "0.25rem 0 0.4rem",
                        background: "var(--vm-surface)",
                        borderTop: "1px solid var(--vm-border)",
                      }}
                    >
                      {expandedLoading && (
                        <div
                          style={{
                            padding: "0.5rem 1.25rem",
                            fontSize: "0.85rem",
                            color: "var(--vm-ink-faint)",
                          }}
                        >
                          Sæki einingar...
                        </div>
                      )}
                      {!expandedLoading &&
                        expandedUnits.map((u) => (
                          <div
                            key={u.fastnum}
                            role="button"
                            tabIndex={0}
                            onClick={() => chooseUnit(u)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                chooseUnit(u);
                              }
                            }}
                            style={{
                              padding: "0.5rem 1.25rem 0.5rem 2rem",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              gap: "1rem",
                              cursor: "pointer",
                              fontSize: "0.88rem",
                            }}
                          >
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                color: "var(--vm-ink)",
                              }}
                            >
                              <UnitIcon code={u.canonical_code} />
                              {u.tegund_raw || formatSegment(u.canonical_code)}
                              {u.einflm != null ? ` · ${formatM2(u.einflm)}` : ""}
                              {u.unit_category
                                ? ` · merking ${u.unit_category}`
                                : ""}
                            </span>
                            <span
                              style={{
                                fontSize: "0.75rem",
                                color: "var(--vm-ink-faint)",
                                fontFamily: "var(--font-mono)",
                              }}
                            >
                              {u.fastnum}
                            </span>
                          </div>
                        ))}
                      {!expandedLoading && expandedUnits.length === 0 && (
                        <div
                          style={{
                            padding: "0.5rem 1.25rem",
                            fontSize: "0.85rem",
                            color: "var(--vm-ink-faint)",
                          }}
                        >
                          Engar einingar tilheyra þessu heimilisfangi.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
