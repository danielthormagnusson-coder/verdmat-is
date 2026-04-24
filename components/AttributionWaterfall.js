"use client";

import { useState } from "react";
import { formatMillions, formatFeatureName } from "@/lib/format";

// DASHBOARD_SPEC_v1 §8 waterfall fix (2026-04-24):
//   * sale_year, sale_month, predicted_at are pure time anchors (WHEN the
//     valuation was priced, not attributes of the property) — hide them from
//     the default waterfall. Their combined ISK impact surfaces as a single
//     footer row "Markaðsstaða" so the math still balances.
//   * age_at_sale stays visible — it IS a property characteristic (how old
//     the home is at sale time). Relabelled to "Aldur við sölu" in
//     lib/format.js so the tooltip phrasing stays coherent.
//   * ?mode=debug bypasses the filter and renders all rows including time
//     anchors.
const TIME_ANCHOR_FEATURES = new Set([
  "sale_year",
  "sale_month",
  "predicted_at",
  // NB: age_at_sale is intentionally NOT in this set — it's a property
  // attribute (aldur við sölu), not a time anchor, even though derived from
  // sale_year. See DASHBOARD_SPEC_v1 §8.2.
]);

const FOOTER_TOOLTIP =
  "Þessi leiðrétting endurspeglar markaðsaðstæður á þeim tíma sem verðmatið var gert (ekki eigninni sjálfri). Notaðu ?mode=debug til að sjá niðurbrot.";

export default function AttributionWaterfall({
  attributions,
  predMean,
  showDebug = false,
}) {
  const [tooltipOpen, setTooltipOpen] = useState(false);

  // Split the full attribution set into visible + hidden so the footer row
  // can reconcile the math for a reader who cross-checks sums.
  const visible = showDebug
    ? [...attributions]
    : attributions.filter((a) => !TIME_ANCHOR_FEATURES.has(a.feature_name));
  const hidden = showDebug
    ? []
    : attributions.filter((a) => TIME_ANCHOR_FEATURES.has(a.feature_name));

  // Sort visible by absolute impact desc, take top 10.
  const top = [...visible]
    .sort((a, b) => Math.abs(b.real_isk_impact) - Math.abs(a.real_isk_impact))
    .slice(0, 10);

  const markadsstada = hidden.reduce(
    (sum, a) => sum + (Number(a.real_isk_impact) || 0),
    0,
  );

  const maxAbs = Math.max(
    ...top.map((a) => Math.abs(a.real_isk_impact)),
    Math.abs(markadsstada),
  );
  if (!maxAbs) return null;

  return (
    <div>
      {top.map((a, i) => {
        const impact = a.real_isk_impact;
        const positive = impact >= 0;
        const widthPct = (Math.abs(impact) / maxAbs) * 50;
        const label = formatFeatureName(a.feature_name);
        const valueDisplay = formatFeatureValue(a.feature_name, a.feature_value);

        return (
          <div
            key={`${a.feature_name}-${i}`}
            style={{
              display: "grid",
              gridTemplateColumns: "1.2fr 2fr 0.8fr",
              alignItems: "center",
              gap: "1rem",
              padding: "0.6rem 0",
              borderBottom: "1px solid var(--vm-border)",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "0.95rem",
                  color: "var(--vm-ink)",
                  marginBottom: "0.1rem",
                }}
              >
                {label}
              </div>
              <div
                style={{ fontSize: "0.8rem", color: "var(--vm-ink-muted)" }}
              >
                {valueDisplay}
              </div>
            </div>
            <div style={{ position: "relative", height: 28 }}>
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  top: 0,
                  bottom: 0,
                  width: 1,
                  background: "var(--vm-border-strong)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  top: 6,
                  bottom: 6,
                  left: positive ? "50%" : `${50 - widthPct}%`,
                  width: `${widthPct}%`,
                  background: positive ? "var(--vm-success)" : "var(--vm-danger)",
                  opacity: 0.85,
                  borderRadius: 3,
                }}
                title={
                  positive
                    ? `+${formatMillions(impact)} — hækkar matið`
                    : `${formatMillions(impact)} — lækkar matið`
                }
              />
            </div>
            <div
              className="tabular"
              style={{
                textAlign: "right",
                color: positive ? "var(--vm-success)" : "var(--vm-danger)",
                fontWeight: 500,
                fontSize: "0.95rem",
              }}
            >
              {positive ? "+" : ""}
              {formatMillions(impact)}
            </div>
          </div>
        );
      })}

      {/* Footer reconciliation row — only in default view when time anchors exist */}
      {hidden.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.2fr 2fr 0.8fr",
            alignItems: "center",
            gap: "1rem",
            padding: "0.6rem 0 0",
            marginTop: "0.3rem",
            borderTop: "2px solid var(--vm-border-strong)",
          }}
        >
          <div style={{ position: "relative" }}>
            <div
              style={{
                fontSize: "0.95rem",
                color: "var(--vm-ink)",
                marginBottom: "0.1rem",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.35rem",
              }}
            >
              Markaðsstaða
              <button
                type="button"
                onClick={() => setTooltipOpen((v) => !v)}
                onBlur={() => setTooltipOpen(false)}
                aria-label="Útskýring"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  border: "1px solid var(--vm-border-strong)",
                  background: "var(--vm-surface)",
                  color: "var(--vm-ink-muted)",
                  fontSize: "0.7rem",
                  cursor: "pointer",
                  padding: 0,
                  lineHeight: 1,
                }}
              >
                ?
              </button>
            </div>
            <div
              style={{ fontSize: "0.8rem", color: "var(--vm-ink-muted)" }}
            >
              tímatengd leiðrétting
            </div>
            {tooltipOpen && (
              <div
                role="tooltip"
                style={{
                  position: "absolute",
                  top: "calc(100% + 4px)",
                  left: 0,
                  zIndex: 5,
                  maxWidth: 300,
                  padding: "0.55rem 0.75rem",
                  background: "var(--vm-surface-elevated)",
                  border: "1px solid var(--vm-border-strong)",
                  borderRadius: 6,
                  fontSize: "0.8rem",
                  color: "var(--vm-ink)",
                  lineHeight: 1.5,
                  boxShadow: "0 4px 16px rgba(19,36,59,0.08)",
                }}
              >
                {FOOTER_TOOLTIP}
              </div>
            )}
          </div>
          <div style={{ position: "relative", height: 28 }}>
            <div
              style={{
                position: "absolute",
                left: "50%",
                top: 0,
                bottom: 0,
                width: 1,
                background: "var(--vm-border-strong)",
              }}
            />
            <div
              style={{
                position: "absolute",
                top: 6,
                bottom: 6,
                left:
                  markadsstada >= 0
                    ? "50%"
                    : `${50 - (Math.abs(markadsstada) / maxAbs) * 50}%`,
                width: `${(Math.abs(markadsstada) / maxAbs) * 50}%`,
                background:
                  markadsstada >= 0
                    ? "var(--vm-primary)"
                    : "var(--vm-ink-muted)",
                opacity: 0.75,
                borderRadius: 3,
              }}
              title="Summa tímatengdra þátta (sale_year, sale_month, predicted_at)"
            />
          </div>
          <div
            className="tabular"
            style={{
              textAlign: "right",
              color: "var(--vm-ink)",
              fontWeight: 500,
              fontSize: "0.95rem",
            }}
          >
            {markadsstada >= 0 ? "+" : ""}
            {formatMillions(markadsstada)}
          </div>
        </div>
      )}
    </div>
  );
}

function formatFeatureValue(name, raw) {
  if (raw == null || raw === "" || raw === "nan") return "—";
  if (name === "EINFLM") return `${parseFloat(raw).toFixed(1)} m²`;
  if (name === "BYGGAR") return `${parseInt(raw, 10)}`;
  if (name === "age_at_sale") return `${parseFloat(raw).toFixed(0)} ár`;
  if (name === "FASTEIGNAMAT" || name === "real_fasteignamat") {
    const n = parseFloat(raw);
    return `${(n / 1000).toFixed(1)} M.kr`;
  }
  if (name === "matsvaedi_bucket") return raw;
  if (name === "sale_year" || name === "sale_month")
    return parseInt(raw, 10);
  if (raw === "true") return "Já";
  if (raw === "false") return "Nei";
  return String(raw).substring(0, 40);
}
