"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  Legend,
} from "recharts";

// Spec §2.4 — three pooled-across-regions lines.
const SEGMENT_CONFIG = [
  { code: "APT_STANDARD", label: "Íbúð", color: "var(--vm-primary)" },
  { code: "SFH_DETACHED", label: "Einbýli", color: "var(--vm-accent)" },
  { code: "ROW_HOUSE", label: "Raðhús", color: "var(--vm-success)" },
];

const ANNOTATIONS = {
  verticalLines: [
    { period: "2008Q2", label: "Hrun byrjar" },
    { period: "2022Q4", label: "Hámark" },
    { period: "2023Q2", label: "Leiðrétting" },
  ],
  shadedBand: {
    start: "2008Q3",
    end: "2011Q1",
    label: "Fall 40%",
  },
};

function Tick({ x, y, payload, fontSize = 11 }) {
  // Show year only, not the full YYYYQN string
  const year = payload.value.slice(0, 4);
  return (
    <text
      x={x}
      y={y + 12}
      textAnchor="middle"
      fill="var(--vm-ink-muted)"
      fontSize={fontSize}
      fontFamily="var(--font-body)"
    >
      {year}
    </text>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div
      style={{
        background: "var(--vm-surface-elevated)",
        border: "1px solid var(--vm-border-strong)",
        borderRadius: 6,
        padding: "0.5rem 0.75rem",
        fontSize: "0.85rem",
        fontFamily: "var(--font-body)",
        color: "var(--vm-ink)",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>{label}</div>
      {payload.map((entry) => {
        const cfg = SEGMENT_CONFIG.find((s) => s.code === entry.dataKey);
        if (!cfg || entry.value == null) return null;
        return (
          <div
            key={entry.dataKey}
            style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem" }}
          >
            <span style={{ color: cfg.color }}>{cfg.label}</span>
            <span className="tabular">
              {entry.value.toFixed(1).replace(".", ",")}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function SegmentTimelineChart({ data }) {
  const ticks = useMemo(() => {
    // Pick one tick per 5 years that exists in data.
    const targets = ["2006Q2", "2010Q1", "2015Q1", "2020Q1", "2026Q1"];
    const periods = new Set(data.map((d) => d.period));
    return targets.filter((t) => periods.has(t));
  }, [data]);

  return (
    <div style={{ width: "100%", height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 24, bottom: 24, left: 0 }}>
          <XAxis
            dataKey="period"
            tick={<Tick />}
            ticks={ticks}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => Math.round(v)}
            tick={{ fontSize: 11, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
            width={44}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "var(--vm-border-strong)" }} />
          <Legend
            verticalAlign="top"
            height={32}
            wrapperStyle={{ fontSize: "0.85rem", fontFamily: "var(--font-body)" }}
            iconType="plainline"
            formatter={(value) => {
              const cfg = SEGMENT_CONFIG.find((s) => s.code === value);
              return cfg ? cfg.label : value;
            }}
          />

          <ReferenceArea
            x1={ANNOTATIONS.shadedBand.start}
            x2={ANNOTATIONS.shadedBand.end}
            fill="var(--vm-accent)"
            fillOpacity={0.06}
            ifOverflow="extendDomain"
          />
          {ANNOTATIONS.verticalLines.map((v) => (
            <ReferenceLine
              key={v.period}
              x={v.period}
              stroke="var(--vm-ink-faint)"
              strokeDasharray="3 3"
              strokeOpacity={0.7}
              label={{
                value: v.label,
                position: "top",
                fill: "var(--vm-ink-muted)",
                fontSize: 10,
              }}
            />
          ))}

          {SEGMENT_CONFIG.map(({ code, color }) => (
            <Line
              key={code}
              type="monotone"
              dataKey={code}
              stroke={color}
              strokeWidth={2}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
