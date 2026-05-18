// Byggingarstig badge — Path C A3.
// Renders a color-coded rounded badge for in-progress construction stages.
// Hidden for B4 (Fullbúið) and null — only B0/B1/B2/B3 surface here.
//
// Color spec (frá A3 spec):
//   B0/B1: amber background, dark text
//   B2:    yellow background, dark text
//   B3:    light-green background, dark text
//
// Tooltip is native `title` attribute — screen-reader-friendly, no JS needed.

import { byggingarstigLabel, isByggingarstigVisible } from "@/lib/format";

const TOOLTIP =
  "Byggingarstig samkvæmt HMS úttektarmanni. Þrjú stig fyrir nýbyggingar og endurbætur áður en eign telst fullbúin (B4).";

const STAGE_STYLES = {
  B0: { background: "#fde7c2", color: "#3a2a0f" }, // amber
  B1: { background: "#fde7c2", color: "#3a2a0f" }, // amber
  B2: { background: "#fff4b0", color: "#3a2f0c" }, // yellow
  B3: { background: "#d6efc7", color: "#1a3a14" }, // light-green
};

export default function ByggingarstigBadge({ stage }) {
  if (!isByggingarstigVisible(stage)) return null;
  const label = byggingarstigLabel(stage);
  const palette = STAGE_STYLES[stage];
  if (!palette || !label) return null;

  return (
    <div
      title={TOOLTIP}
      role="status"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.4rem",
        padding: "0.35rem 0.75rem",
        borderRadius: 999,
        background: palette.background,
        color: palette.color,
        fontSize: "0.82rem",
        fontWeight: 600,
        letterSpacing: "0.01em",
        marginBottom: "0.5rem",
        cursor: "help",
      }}
    >
      <span aria-hidden="true">⏳</span>
      Á byggingarstigi {stage} — {label}
    </div>
  );
}
