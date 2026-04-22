"use client";

import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from "recharts";
import { formatSegment } from "@/lib/format";

const DEFAULT_ROWS = ["APT_FLOOR", "APT_STANDARD", "SFH_DETACHED", "ROW_HOUSE"];

// Row dropdown options — default rows first, secondary variants after.
const ROW_OPTIONS = [
  "APT_FLOOR",
  "APT_STANDARD",
  "SFH_DETACHED",
  "ROW_HOUSE",
  "APT_BASEMENT",
  "APT_ATTIC",
  "SEMI_DETACHED",
  "SUMMERHOUSE",
];

const REGIONS = ["RVK_core", "Capital_sub", "Country"];
const REGION_LABEL = {
  RVK_core: "Reykjavík miðja",
  Capital_sub: "Höfuðborgarsvæðið",
  Country: "Landsbyggðin",
};

const SEGMENT_COLOR = {
  APT_FLOOR: "var(--vm-primary)",
  APT_STANDARD: "var(--vm-primary)",
  SFH_DETACHED: "var(--vm-accent)",
  ROW_HOUSE: "var(--vm-success)",
  APT_BASEMENT: "var(--vm-ink-muted)",
  APT_ATTIC: "var(--vm-ink-muted)",
  SEMI_DETACHED: "var(--vm-cold)",
  SUMMERHOUSE: "var(--vm-hot)",
};

const CRASH_BAND = { start: "2008Q3", end: "2011Q1" };

// Data-quality → crash-band styling (§3.3 table).
function crashBandStyle(quality) {
  switch (quality) {
    case "high":
      return { fill: "var(--vm-accent)", fillOpacity: 0.08 };
    case "medium":
      return { fill: "var(--vm-accent)", fillOpacity: 0.05 };
    case "low":
      return { fill: "var(--vm-accent)", fillOpacity: 0.03 };
    default:
      return { fill: "transparent", fillOpacity: 0 };
  }
}

function currentQuality(rows) {
  // Worst-case quality over the crash band (2008Q3–2011Q1) drives band opacity.
  // If any row in band is insufficient, dim whole cell.
  const in_band = rows.filter(
    (r) =>
      r.period >= CRASH_BAND.start &&
      r.period <= CRASH_BAND.end,
  );
  if (in_band.length === 0) return "insufficient";
  const ranks = { high: 3, medium: 2, low: 1, insufficient: 0 };
  return in_band.reduce(
    (acc, r) =>
      (ranks[r.data_quality] ?? 0) < ranks[acc] ? r.data_quality : acc,
    "high",
  );
}

function insufficientCell(rows) {
  // Spec §3.3: greyed, "Of fá pör" if cell has <50 fitted pairs (cell-level).
  if (rows.length === 0) return true;
  const latest = rows[rows.length - 1];
  return latest?.insufficient_sample === true;
}

function latestIndex(rows, key) {
  for (let i = rows.length - 1; i >= 0; i--) {
    const v = rows[i][key];
    if (v != null) return Number(v);
  }
  return null;
}

function ChartTooltip({ active, payload, label, segment, region, mode }) {
  if (!active || !payload || payload.length === 0) return null;
  const row = payload[0].payload;
  const modeLabel = mode === "real" ? "Raunverð" : "Nominal";
  const otherKey = mode === "real" ? "index_value_nominal" : "index_value_real";
  const otherLabel = mode === "real" ? "Nominal" : "Raunverð";
  const val = payload[0].value;
  const other = row[otherKey];
  const ci = row[mode === "real" ? "std_error_real" : "std_error_nominal"];
  return (
    <div
      style={{
        background: "var(--vm-surface-elevated)",
        border: "1px solid var(--vm-border-strong)",
        borderRadius: 6,
        padding: "0.45rem 0.65rem",
        fontSize: "0.8rem",
        color: "var(--vm-ink)",
        fontFamily: "var(--font-body)",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 2 }}>
        {label} · {formatSegment(segment)} × {REGION_LABEL[region] || region}
      </div>
      <div>
        {modeLabel} index: <span className="tabular">{val?.toFixed(1).replace(".", ",")}</span>
      </div>
      {other != null && (
        <div style={{ color: "var(--vm-ink-muted)" }}>
          {otherLabel}:{" "}
          <span className="tabular">{Number(other).toFixed(1).replace(".", ",")}</span>
        </div>
      )}
      {row.n_pairs_in_period != null && (
        <div style={{ color: "var(--vm-ink-muted)" }}>
          n pör ársfjórðung: <span className="tabular">{row.n_pairs_in_period}</span>
        </div>
      )}
      {ci != null && (
        <div style={{ color: "var(--vm-ink-muted)" }}>
          CI ±: <span className="tabular">±{Number(ci).toFixed(2).replace(".", ",")}</span>
        </div>
      )}
    </div>
  );
}

function SubChart({ segment, region, rows, mode }) {
  const insufficient = insufficientCell(rows);
  const band = crashBandStyle(currentQuality(rows));
  const color = SEGMENT_COLOR[segment] || "var(--vm-ink-muted)";
  const dataKey = mode === "real" ? "index_value_real" : "index_value_nominal";
  const currentIdx = latestIndex(rows, dataKey);

  return (
    <div
      style={{
        padding: "0.5rem",
        opacity: insufficient ? 0.55 : 1,
        position: "relative",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.72rem",
          marginBottom: "0.25rem",
          fontWeight: 500,
          color: "var(--vm-ink-muted)",
        }}
      >
        <span>{REGION_LABEL[region] || region}</span>
        {currentIdx != null ? (
          <span className="tabular" style={{ color: "var(--vm-ink)" }}>
            {currentIdx.toFixed(0)}
          </span>
        ) : (
          <span>—</span>
        )}
      </div>
      <div style={{ width: "100%", height: 130 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 2, right: 6, bottom: 16, left: 0 }}>
            <XAxis
              dataKey="period"
              ticks={["2006Q2", "2015Q1", "2026Q2"]}
              tick={{ fontSize: 9, fill: "var(--vm-ink-faint)" }}
              axisLine={{ stroke: "var(--vm-border)" }}
              tickLine={false}
              tickFormatter={(v) => v.slice(0, 4)}
            />
            <YAxis hide domain={["auto", "auto"]} />
            <Tooltip
              content={(p) => (
                <ChartTooltip {...p} segment={segment} region={region} mode={mode} />
              )}
              cursor={{ stroke: "var(--vm-border-strong)" }}
            />
            <ReferenceArea x1={CRASH_BAND.start} x2={CRASH_BAND.end} {...band} />
            <ReferenceLine y={100} stroke="var(--vm-border)" strokeDasharray="2 3" />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={1.8}
              dot={false}
              isAnimationActive={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {insufficient && (
        <p
          style={{
            fontSize: "0.7rem",
            color: "var(--vm-ink-faint)",
            marginTop: "0.2rem",
            textAlign: "center",
          }}
        >
          Of fá pör (n &lt; 50 / ársfj.)
        </p>
      )}
    </div>
  );
}

function RowPicker({ value, onChange }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        background: "var(--vm-surface)",
        border: "1px solid var(--vm-border)",
        borderRadius: 4,
        padding: "0.3rem 0.5rem",
        fontSize: "0.8rem",
        fontFamily: "var(--font-body)",
        color: "var(--vm-ink)",
        cursor: "pointer",
      }}
    >
      {ROW_OPTIONS.map((seg) => (
        <option key={seg} value={seg}>
          {formatSegment(seg)}
        </option>
      ))}
    </select>
  );
}

function ModeToggle({ value, onChange }) {
  const Btn = ({ v, label }) => (
    <button
      type="button"
      onClick={() => onChange(v)}
      aria-pressed={value === v}
      style={{
        padding: "0.35rem 0.85rem",
        border: "1px solid var(--vm-border-strong)",
        borderLeftWidth: v === "real" ? 1 : 0,
        background:
          value === v ? "var(--vm-primary)" : "var(--vm-surface)",
        color:
          value === v ? "var(--vm-surface)" : "var(--vm-ink-muted)",
        fontSize: "0.85rem",
        cursor: "pointer",
        borderRadius: v === "real" ? "4px 0 0 4px" : "0 4px 4px 0",
        fontFamily: "var(--font-body)",
        fontWeight: 500,
      }}
    >
      {label}
    </button>
  );
  return (
    <div role="group" aria-label="Real vs Nominal">
      <Btn v="real" label="Raun" />
      <Btn v="nominal" label="Nominal" />
    </div>
  );
}

export default function VisitalaGrid({ allRows }) {
  // allRows shape: [{canonical_code, region_tier, year, quarter, period,
  //   index_value_real, index_value_nominal, n_pairs_in_period,
  //   std_error_real, std_error_nominal, data_quality, insufficient_sample}]

  const [mode, setMode] = useState("real");
  const [rows, setRows] = useState(DEFAULT_ROWS);

  // Pre-group data for fast lookups.
  const byCell = useMemo(() => {
    const map = new Map();
    for (const r of allRows) {
      const key = `${r.canonical_code}|${r.region_tier}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(r);
    }
    return map;
  }, [allRows]);

  const fittedCells = useMemo(() => {
    let fitted = 0;
    let total = 0;
    for (const [, cellRows] of byCell) {
      total += 1;
      if (!insufficientCell(cellRows)) fitted += 1;
    }
    return { fitted, total };
  }, [byCell]);

  const setRow = (i, seg) => {
    const next = [...rows];
    next[i] = seg;
    setRows(next);
  };

  return (
    <>
      <div
        style={{
          display: "flex",
          gap: "1rem",
          alignItems: "center",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        <ModeToggle value={mode} onChange={setMode} />
        <span
          style={{
            fontSize: "0.8rem",
            color: "var(--vm-ink-faint)",
          }}
        >
          81 ársfjórðungar · {fittedCells.fitted}/{fittedCells.total} reitir pöruðir
        </span>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.25rem",
          border: "1px solid var(--vm-border)",
          borderRadius: 8,
          overflow: "hidden",
          background: "var(--vm-surface-elevated)",
        }}
      >
        {/* Header row of region labels */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "200px repeat(3, 1fr)",
            gap: "0.5rem",
            alignItems: "center",
            padding: "0.6rem 0.85rem",
            borderBottom: "1px solid var(--vm-border)",
            fontSize: "0.8rem",
            fontWeight: 600,
            color: "var(--vm-ink-muted)",
          }}
        >
          <span />
          {REGIONS.map((reg) => (
            <span key={reg}>{REGION_LABEL[reg]}</span>
          ))}
        </div>

        {rows.map((seg, i) => (
          <div
            key={`${seg}-${i}`}
            style={{
              display: "grid",
              gridTemplateColumns: "200px repeat(3, 1fr)",
              gap: "0.5rem",
              alignItems: "start",
              padding: "0.4rem 0.85rem 0.85rem",
              borderBottom:
                i === rows.length - 1 ? "none" : "1px solid var(--vm-border)",
            }}
          >
            <div
              style={{
                paddingTop: "0.5rem",
                fontSize: "0.9rem",
                display: "flex",
                flexDirection: "column",
                gap: "0.35rem",
              }}
            >
              <strong style={{ color: "var(--vm-ink)" }}>
                {formatSegment(seg)}
              </strong>
              <RowPicker value={seg} onChange={(v) => setRow(i, v)} />
            </div>
            {REGIONS.map((region) => {
              const rowsForCell =
                byCell.get(`${seg}|${region}`) || [];
              return (
                <SubChart
                  key={region}
                  segment={seg}
                  region={region}
                  rows={rowsForCell}
                  mode={mode}
                />
              );
            })}
          </div>
        ))}
      </div>
    </>
  );
}
