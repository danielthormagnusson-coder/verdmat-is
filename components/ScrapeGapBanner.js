"use client";

import { useEffect, useState } from "react";

/**
 * Spec §2.6 — low-key scrape-gap disclaimer. Session-scoped dismissal via
 * sessionStorage; re-appears on next session.
 */
export default function ScrapeGapBanner() {
  // SSR renders visible so the disclosure reaches users/crawlers on first paint;
  // the effect re-hides it when a prior session dismissed.
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const stored =
      typeof window !== "undefined" &&
      sessionStorage.getItem("scrapeGapDismissed") === "1";
    if (stored) setDismissed(true);
  }, []);

  if (dismissed) return null;

  const handleDismiss = () => {
    try {
      sessionStorage.setItem("scrapeGapDismissed", "1");
    } catch {
      // sessionStorage may be unavailable (privacy mode) — silently ignore.
    }
    setDismissed(true);
  };

  return (
    <div
      role="status"
      aria-label="Upplýsingar um gögn"
      style={{
        display: "inline-flex",
        alignItems: "flex-start",
        gap: "0.6rem",
        background: "rgba(212, 179, 70, 0.10)",
        border: "1px solid rgba(212, 179, 70, 0.35)",
        borderRadius: "6px",
        padding: "0.55rem 0.85rem",
        fontSize: "0.9rem",
        lineHeight: 1.4,
        color: "var(--vm-ink-muted)",
        maxWidth: 760,
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
        Takmörkuð gögn frá júlí 2025 vegna tímabundinnar breytingar á
        auglýsingaflæði. Historical analytics eru óháð þessu.
      </span>
      <button
        type="button"
        onClick={handleDismiss}
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
