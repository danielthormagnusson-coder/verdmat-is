"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { formatSegment, formatM2 } from "@/lib/format";

export default function SearchAutocomplete() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(-1);
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
      return;
    }
    const handle = setTimeout(async () => {
      setLoading(true);
      const term = q.trim();
      let query = supabase
        .from("properties")
        .select("fastnum, heimilisfang, postnr, postheiti, canonical_code, einflm")
        .eq("is_residential", true)
        .limit(8);

      if (/^\d+$/.test(term)) {
        // If searching by fastnum, don't filter residential — user may look up a
        // specific fastnum that's non-residential (detail page shows info but
        // omits the valuation card for non-residential).
        query = supabase
          .from("properties")
          .select("fastnum, heimilisfang, postnr, postheiti, canonical_code, einflm")
          .eq("fastnum", Number(term))
          .limit(8);
      } else {
        const pattern = `%${term}%`;
        query = query.or(
          `heimilisfang.ilike.${pattern},postheiti.ilike.${pattern}`
        );
      }
      const { data } = await query;
      setResults(data || []);
      setLoading(false);
      setOpen(true);
      setActive(-1);
    }, 220);
    return () => clearTimeout(handle);
  }, [q]);

  function choose(r) {
    setOpen(false);
    router.push(`/eign/${r.fastnum}`);
  }

  function onKey(e) {
    if (!open || results.length === 0) {
      if (e.key === "Enter" && /^\d+$/.test(q.trim())) {
        router.push(`/eign/${q.trim()}`);
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const idx = active >= 0 ? active : 0;
      if (results[idx]) choose(results[idx]);
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
          placeholder="Leita að heimilisfangi eða fastanúmeri..."
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
            if (results[0]) choose(results[0]);
            else if (/^\d+$/.test(q.trim())) router.push(`/eign/${q.trim()}`);
          }}
        >
          Fá verðmat
        </button>
      </div>
      {open && (loading || results.length > 0) && (
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
          {!loading &&
            results.map((r, i) => (
              <div
                key={r.fastnum}
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(r)}
                style={{
                  padding: "0.75rem 1rem",
                  borderTop: i === 0 ? "none" : "1px solid var(--vm-border)",
                  cursor: "pointer",
                  background:
                    active === i ? "var(--vm-surface)" : "transparent",
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
                    {r.heimilisfang}
                  </div>
                  <div
                    style={{
                      fontSize: "0.85rem",
                      color: "var(--vm-ink-muted)",
                    }}
                  >
                    {r.postnr} {r.postheiti} · {formatSegment(r.canonical_code)}{" "}
                    {r.einflm ? `· ${formatM2(r.einflm)}` : ""}
                  </div>
                </div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--vm-ink-faint)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {r.fastnum}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
