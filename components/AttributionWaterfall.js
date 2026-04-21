"use client";

import { formatMillions, formatFeatureName } from "@/lib/format";

export default function AttributionWaterfall({ attributions, predMean }) {
  // Sort by absolute impact desc, take top 10
  const top = [...attributions]
    .sort((a, b) => Math.abs(b.real_isk_impact) - Math.abs(a.real_isk_impact))
    .slice(0, 10);

  const maxAbs = Math.max(...top.map((a) => Math.abs(a.real_isk_impact)));
  if (!maxAbs) return null;

  return (
    <div>
      {top.map((a, i) => {
        const impact = a.real_isk_impact;
        const positive = impact >= 0;
        const widthPct = (Math.abs(impact) / maxAbs) * 50; // 50% because bars go out from center
        const label = formatFeatureName(a.feature_name);
        const valueDisplay = formatFeatureValue(a.feature_name, a.feature_value);

        return (
          <div
            key={i}
            style={{
              display: "grid",
              gridTemplateColumns: "1.2fr 2fr 0.8fr",
              alignItems: "center",
              gap: "1rem",
              padding: "0.6rem 0",
              borderBottom:
                i < top.length - 1 ? "1px solid var(--vm-border)" : "none",
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
              {/* Center line */}
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
              {/* Bar */}
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
  if (name === "sale_year" || name === "sale_month") return parseInt(raw, 10);
  if (raw === "true") return "Já";
  if (raw === "false") return "Nei";
  return String(raw).substring(0, 40);
}
