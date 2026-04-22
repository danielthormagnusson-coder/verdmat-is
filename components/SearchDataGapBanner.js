"use client";

import { useEffect, useState } from "react";

// Bug 4 + Search UX overhaul (2026-04-22): permanent belt under the homepage
// search field that explains why the result set may be incomplete. Persists
// dismissal across sessions via localStorage (not sessionStorage — user should
// need to dismiss once per browser, not every visit).

const STORAGE_KEY = "verdmat.searchDataGap.dismissed";

export default function SearchDataGapBanner() {
  // SSR: render visible so non-JS + SEO see the caveat. Client hides after
  // hydration if the user has dismissed.
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    try {
      if (
        typeof window !== "undefined" &&
        localStorage.getItem(STORAGE_KEY) === "1"
      ) {
        setDismissed(true);
      }
    } catch {
      // localStorage may be blocked in some privacy modes — silently noop.
    }
  }, []);

  if (dismissed) return null;

  const dismiss = () => {
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // ignore
    }
    setDismissed(true);
  };

  return (
    <div
      role="note"
      aria-label="Upplýsingar um gagnasafn"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "0.6rem",
        marginTop: "1rem",
        padding: "0.55rem 0.9rem",
        background: "rgba(212, 179, 70, 0.10)",
        border: "1px solid rgba(212, 179, 70, 0.32)",
        borderRadius: 6,
        fontSize: "0.85rem",
        color: "var(--vm-ink-muted)",
        lineHeight: 1.45,
      }}
    >
      <span
        aria-hidden
        style={{
          color: "rgba(184, 148, 38, 0.9)",
          fontSize: "1rem",
          lineHeight: 1.4,
          flexShrink: 0,
        }}
      >
        ⓘ
      </span>
      <span style={{ flex: 1 }}>
        Gagnasafn okkar byggir á HMS fasteignaskrá. Nýjar eignir og nýbyggingar
        birtast ekki allar í leit — við erum að byggja fyllra gagnasafn.
      </span>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Loka"
        style={{
          background: "transparent",
          border: "none",
          color: "var(--vm-ink-faint)",
          cursor: "pointer",
          padding: "0 0.25rem",
          fontSize: "1.1rem",
          lineHeight: 1,
          flexShrink: 0,
        }}
      >
        ×
      </button>
    </div>
  );
}
