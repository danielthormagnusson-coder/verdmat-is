"use client";

import { useState } from "react";
import { formatMillions } from "@/lib/format";

// Viðmiðunarverðmöt strip — Path C A1.
// Renders up to 3 pillars under the spec-card:
//   1. HMS-fasteignamat (current)               — always visible if non-null
//   2. Brunabótamat                             — hidden if null
//   3. HMS spá [next-year] + delta vs current   — hidden if null OR |Δ| < 2%
// Tooltips are click-to-toggle; closing on blur.
//
// All three valuation columns are stored in HMS' "thousand kr" unit (same as
// the existing `fasteignamat` column) — multiply by 1000 before formatMillions.

const TOOLTIP_BRUNABOT =
  "Áætlaður endurbyggingarkostnaður frá HMS. Óháð markaðsverði.";
const TOOLTIP_SPA =
  "Næsta árs fasteignamat samkvæmt HMS, birt í júní.";

function nextYearLabel() {
  return new Date().getFullYear() + 1;
}

export default function ValuationStrip({
  fasteignamat,
  brunabotamat,
  fasteignamatNaestaAr,
}) {
  const [open, setOpen] = useState(null); // 'brunabot' | 'spa' | null

  // Compute spá delta — only render pillar 3 if magnitude >= 2%.
  let spaPillar = null;
  if (
    fasteignamatNaestaAr != null &&
    fasteignamatNaestaAr > 0 &&
    fasteignamat != null &&
    fasteignamat > 0
  ) {
    const deltaFrac = (fasteignamatNaestaAr - fasteignamat) / fasteignamat;
    if (Math.abs(deltaFrac) >= 0.02) {
      spaPillar = {
        value: fasteignamatNaestaAr,
        deltaFrac,
      };
    }
  }

  const showFastmat = fasteignamat != null && fasteignamat > 0;
  const showBrunabot = brunabotamat != null && brunabotamat > 0;
  const showSpa = spaPillar !== null;

  if (!showFastmat && !showBrunabot && !showSpa) return null;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "1.25rem 2rem",
        padding: "0.9rem 1.25rem",
        background: "var(--vm-surface)",
        borderRadius: 10,
        border: "1px solid var(--vm-border)",
        marginBottom: "0.9rem",
      }}
    >
      {showFastmat && (
        <Pillar
          label="HMS-fasteignamat"
          value={formatMillions(fasteignamat * 1000, 1)}
        />
      )}
      {showBrunabot && (
        <Pillar
          label="Brunabótamat"
          value={formatMillions(brunabotamat * 1000, 1)}
          tooltipText={TOOLTIP_BRUNABOT}
          open={open === "brunabot"}
          onToggle={() => setOpen(open === "brunabot" ? null : "brunabot")}
        />
      )}
      {showSpa && (
        <Pillar
          label={`HMS spá ${nextYearLabel()}`}
          value={formatSpa(spaPillar.value, spaPillar.deltaFrac)}
          tooltipText={TOOLTIP_SPA}
          open={open === "spa"}
          onToggle={() => setOpen(open === "spa" ? null : "spa")}
        />
      )}
    </div>
  );
}

function formatSpa(naestaAr, deltaFrac) {
  const main = formatMillions(naestaAr * 1000, 1);
  const pct = (deltaFrac * 100).toFixed(1).replace(".", ",");
  const sign = deltaFrac >= 0 ? "+" : "";
  return `${main} (${sign}${pct}%)`;
}

function Pillar({ label, value, tooltipText, open, onToggle }) {
  return (
    <div style={{ position: "relative", minWidth: 0 }}>
      <div
        style={{
          fontSize: "0.72rem",
          color: "var(--vm-ink-faint)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: "0.2rem",
          display: "inline-flex",
          alignItems: "center",
          gap: "0.35rem",
        }}
      >
        {label}
        {tooltipText && (
          <button
            type="button"
            onClick={onToggle}
            onBlur={() => open && onToggle()}
            aria-label="Útskýring"
            aria-expanded={open}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 16,
              height: 16,
              borderRadius: "50%",
              border: "1px solid var(--vm-border-strong)",
              background: "var(--vm-surface-elevated, var(--vm-surface))",
              color: "var(--vm-ink-muted)",
              fontSize: "0.65rem",
              cursor: "pointer",
              padding: 0,
              lineHeight: 1,
            }}
          >
            i
          </button>
        )}
      </div>
      <div style={{ fontWeight: 500 }} className="tabular">
        {value}
      </div>
      {open && tooltipText && (
        <div
          role="tooltip"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            zIndex: 5,
            maxWidth: 280,
            padding: "0.55rem 0.75rem",
            background: "var(--vm-surface-elevated, var(--vm-surface))",
            border: "1px solid var(--vm-border-strong)",
            borderRadius: 6,
            fontSize: "0.8rem",
            color: "var(--vm-ink)",
            lineHeight: 1.5,
            boxShadow: "0 4px 16px rgba(19,36,59,0.08)",
          }}
        >
          {tooltipText}
        </div>
      )}
    </div>
  );
}
