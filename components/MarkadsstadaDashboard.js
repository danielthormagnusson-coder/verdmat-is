"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
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

// DASHBOARD_SPEC_v1 §4 + Bug 6 methodology refinement (2026-04-24):
//   * Primary display is quarterly per-cell regime (stable, long-window method).
//   * Monthly toggle exposes the z_3v12-smoothed regime for advanced drill-down.
//   * Per-cell sample-size fallback: if monthly n < 50, display falls back to
//     the quarterly regime inline, with a "Ársfjórðungslegt" disclosure.

const SEGMENTS = [
  "APT_FLOOR",
  "APT_STANDARD",
  "SFH_DETACHED",
  "ROW_HOUSE",
  "APT_BASEMENT",
  "SEMI_DETACHED",
  "APT_ATTIC",
];
const REGIONS = ["RVK_core", "Capital_sub", "Country"];
const REGION_LABEL = {
  RVK_core: "Reykjavík miðja",
  Capital_sub: "Höfuðborgarsvæðið",
  Country: "Landsbyggðin",
};
const MAIN_RESIDENTIAL = ["APT_FLOOR", "APT_STANDARD", "SFH_DETACHED", "ROW_HOUSE"];

const GAP_START = "2025-07";

function pillClass(bucket) {
  if (bucket === "hot") return "vm-badge-hot";
  if (bucket === "cold") return "vm-badge-cold";
  if (bucket === "neutral") return "vm-badge-neutral";
  return "vm-badge-neutral";
}
function pillLabel(bucket) {
  if (bucket === "hot") return "HEITUR";
  if (bucket === "cold") return "KALDUR";
  if (bucket === "neutral") return "HLUTLAUS";
  return "—";
}

function monthToQuarter(m) {
  if (!m) return null;
  const [y, mm] = m.split("-");
  const q = Math.ceil(Number(mm) / 3);
  return `${y}Q${q}`;
}
function formatMonth(m) {
  const months = ["jan","feb","mar","apr","maí","jún","júl","ágú","sep","okt","nóv","des"];
  if (!m) return "—";
  const [y, mm] = m.split("-");
  return `${months[Number(mm) - 1]} ${y}`;
}
function formatQuarter(q) {
  if (!q) return "—";
  const [y, qq] = q.split("Q");
  const monthsInQ = { 1: "jan–mar", 2: "apr–jún", 3: "júl–sep", 4: "okt–des" };
  return `${q} · ${monthsInQ[Number(qq)]} ${y}`;
}

function PoolMonthlyTimeline({ rows, selectedMonth, allMonths }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={rows} margin={{ top: 8, right: 24, bottom: 24, left: 0 }}>
        <XAxis
          dataKey="month"
          ticks={allMonths.filter((_, i) => i % 18 === 0)}
          tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
          axisLine={{ stroke: "var(--vm-border)" }}
          tickLine={false}
          tickFormatter={(v) => v.slice(0, 4)}
        />
        <YAxis
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
          tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
          axisLine={{ stroke: "var(--vm-border)" }}
          tickLine={false}
          width={40}
        />
        <Tooltip
          contentStyle={{
            background: "var(--vm-surface-elevated)",
            border: "1px solid var(--vm-border-strong)",
            borderRadius: 6,
            fontSize: "0.8rem",
            fontFamily: "var(--font-body)",
            color: "var(--vm-ink)",
          }}
          formatter={(v) => [`${(Number(v) * 100).toFixed(1).replace(".", ",")}%`, "Yfirboð"]}
          labelFormatter={formatMonth}
        />
        <ReferenceArea
          x1={GAP_START}
          x2={rows.length ? rows[rows.length - 1].month : GAP_START}
          fill="rgba(212, 179, 70, 0.18)"
          fillOpacity={1}
        />
        {selectedMonth && (
          <ReferenceLine
            x={selectedMonth}
            stroke="var(--vm-primary)"
            strokeWidth={2}
            strokeDasharray="4 3"
          />
        )}
        <Line
          type="monotone"
          dataKey="pooled_rate"
          stroke="var(--vm-primary)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function CellPopover({ cellRows, segment, region, selectedMonth, mode, onClose }) {
  // cellRows = all regime_per_cell_monthly rows for this cell (asc by month)
  // + quarterlyByCell map — this component receives both.
  const mini = cellRows
    .slice(-12)
    .map((r) => ({ month: r.month, rate: r.above_list_rate != null ? Number(r.above_list_rate) : null }));
  const latestForMonth = cellRows.find((r) => r.month === selectedMonth) ?? cellRows[cellRows.length - 1];
  return (
    <div
      role="dialog"
      aria-label="Reitupplýsingar"
      style={{
        position: "absolute",
        top: "calc(100% + 6px)",
        left: 0,
        zIndex: 10,
        minWidth: 260,
        background: "var(--vm-surface-elevated)",
        border: "1px solid var(--vm-border-strong)",
        borderRadius: 6,
        padding: "0.75rem",
        boxShadow: "0 4px 16px rgba(19,36,59,0.08)",
      }}
    >
      <button
        type="button"
        onClick={onClose}
        aria-label="Loka"
        style={{
          position: "absolute",
          top: 4,
          right: 8,
          background: "transparent",
          border: "none",
          cursor: "pointer",
          color: "var(--vm-ink-faint)",
          fontSize: "1rem",
        }}
      >
        ×
      </button>
      <p
        style={{
          fontSize: "0.75rem",
          fontWeight: 600,
          color: "var(--vm-ink-muted)",
          margin: 0,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {formatSegment(segment)} · {REGION_LABEL[region] || region}
      </p>
      {latestForMonth ? (
        <>
          <p
            style={{
              fontSize: "0.8rem",
              color: "var(--vm-ink-muted)",
              margin: "0.45rem 0 0.2rem",
            }}
          >
            <strong style={{ color: "var(--vm-ink)" }}>
              {pillLabel(
                mode === "quarterly"
                  ? latestForMonth.quarterly_regime
                  : latestForMonth.display_regime,
              )}
            </strong>
            {" · "}
            {mode === "quarterly"
              ? `ársfj. ${latestForMonth.quarterly_period ?? "—"} (n=${latestForMonth.quarterly_n_pairs ?? "—"})`
              : latestForMonth.regime_source === "quarterly_fallback"
              ? `fallback til ársfj. ${latestForMonth.quarterly_period ?? "—"} (n mán ${latestForMonth.n_month ?? "—"} < 50)`
              : `smoothed z=${
                  latestForMonth.z_3v12 != null
                    ? Number(latestForMonth.z_3v12).toFixed(2).replace(".", ",")
                    : "—"
                } (n mán ${latestForMonth.n_month ?? "—"})`}
          </p>
          {latestForMonth.above_list_rate != null && (
            <p style={{ fontSize: "0.78rem", color: "var(--vm-ink-muted)", margin: 0 }}>
              Yfirboð: {(Number(latestForMonth.above_list_rate) * 100).toFixed(0)} %
            </p>
          )}
        </>
      ) : null}
      <div style={{ width: "100%", height: 80, marginTop: "0.5rem" }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={mini} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
            <XAxis dataKey="month" hide />
            <YAxis hide domain={["auto", "auto"]} />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="var(--vm-primary)"
              strokeWidth={1.6}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p style={{ fontSize: "0.7rem", color: "var(--vm-ink-faint)", margin: "0.35rem 0 0" }}>
        12 mán. yfirboð
      </p>
      <Link
        href={`/markadur/visitala#${segment}.${region}`}
        style={{ fontSize: "0.8rem", color: "var(--vm-primary)", display: "inline-block", marginTop: "0.5rem" }}
      >
        Skoða vísitölu →
      </Link>
    </div>
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
        borderLeftWidth: v === "quarterly" ? 1 : 0,
        background: value === v ? "var(--vm-primary)" : "var(--vm-surface)",
        color: value === v ? "var(--vm-surface)" : "var(--vm-ink-muted)",
        fontSize: "0.82rem",
        cursor: "pointer",
        borderRadius: v === "quarterly" ? "4px 0 0 4px" : "0 4px 4px 0",
        fontFamily: "var(--font-body)",
        fontWeight: 500,
      }}
    >
      {label}
    </button>
  );
  return (
    <div role="group" aria-label="Tímaupplausn">
      <Btn v="quarterly" label="Ársfjórðungslegt" />
      <Btn v="monthly" label="Mánaðarlegt (smoothed)" />
    </div>
  );
}

export default function MarkadsstadaDashboard({ monthlyRows }) {
  // monthlyRows: rows from regime_per_cell_monthly view. Contains raw_regime,
  // smoothed_regime, quarterly_regime, display_regime, regime_source.

  const allMonths = useMemo(
    () => Array.from(new Set(monthlyRows.map((r) => r.month))).sort(),
    [monthlyRows],
  );
  const latestMonth = allMonths[allMonths.length - 1];
  const [selectedMonth, setSelectedMonth] = useState(latestMonth || "");
  const [mode, setMode] = useState("quarterly"); // default per Bug 6 fix
  const [openCell, setOpenCell] = useState(null);

  const byCell = useMemo(() => {
    const m = new Map();
    for (const r of monthlyRows) {
      const k = `${r.canonical_code}|${r.region_tier}`;
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(r);
    }
    for (const arr of m.values()) arr.sort((a, b) => a.month.localeCompare(b.month));
    return m;
  }, [monthlyRows]);

  const cellAt = (seg, reg, month) => {
    const arr = byCell.get(`${seg}|${reg}`) || [];
    let best = null;
    for (const r of arr) {
      if (r.month <= month) best = r;
      else break;
    }
    return best;
  };

  const pooledAboveList = useMemo(() => {
    const m = new Map();
    for (const r of monthlyRows) {
      if (!MAIN_RESIDENTIAL.includes(r.canonical_code)) continue;
      if (!REGIONS.includes(r.region_tier)) continue;
      if (r.above_list_rate == null || r.n_month == null) continue;
      if (!m.has(r.month)) m.set(r.month, { weighted: 0, total: 0 });
      const agg = m.get(r.month);
      agg.weighted += Number(r.above_list_rate) * Number(r.n_month);
      agg.total += Number(r.n_month);
    }
    return Array.from(m.entries())
      .map(([month, { weighted, total }]) => ({
        month,
        pooled_rate: total > 0 ? weighted / total : null,
      }))
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [monthlyRows]);

  const selectedQuarter = monthToQuarter(selectedMonth);
  const inGap = selectedMonth >= GAP_START;
  const monthIndex = allMonths.indexOf(selectedMonth);
  const headerDate =
    mode === "quarterly"
      ? formatQuarter(selectedQuarter)
      : formatMonth(selectedMonth);

  return (
    <>
      {/* Slider + mode toggle */}
      <section
        className="vm-card"
        style={{ marginBottom: "1.5rem", padding: "1.25rem 1.5rem" }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: "0.5rem",
            gap: "1rem",
            flexWrap: "wrap",
          }}
        >
          <span style={{ fontSize: "0.8rem", color: "var(--vm-ink-muted)", fontWeight: 600 }}>
            Tímabil
          </span>
          <ModeToggle value={mode} onChange={setMode} />
          <span className="tabular" style={{ fontSize: "0.95rem", color: "var(--vm-ink)" }}>
            {headerDate}
          </span>
        </div>
        <div style={{ position: "relative" }}>
          <div
            aria-hidden
            style={{
              position: "absolute",
              top: 6,
              bottom: 6,
              left: `${Math.max(0, (allMonths.indexOf(GAP_START) / Math.max(allMonths.length - 1, 1)) * 100)}%`,
              right: 0,
              background:
                "repeating-linear-gradient(45deg, rgba(212,179,70,0.12) 0 6px, rgba(212,179,70,0.28) 6px 12px)",
              borderRadius: 4,
              pointerEvents: "none",
            }}
          />
          <input
            type="range"
            min={0}
            max={Math.max(allMonths.length - 1, 0)}
            value={Math.max(monthIndex, 0)}
            onChange={(e) => setSelectedMonth(allMonths[Number(e.target.value)])}
            aria-label="Veldu tímabil"
            style={{
              width: "100%",
              position: "relative",
              zIndex: 1,
              accentColor: "var(--vm-primary)",
            }}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.7rem",
              color: "var(--vm-ink-faint)",
              marginTop: 2,
            }}
          >
            <span>{allMonths[0]}</span>
            <span>{allMonths[allMonths.length - 1]}</span>
          </div>
        </div>
        {inGap && (
          <p style={{ fontSize: "0.8rem", color: "var(--vm-ink-muted)", marginTop: "0.5rem" }}>
            ⚠ Heat-labels reikna á takmörkuðum gögnum frá júlí 2025.
          </p>
        )}
      </section>

      {/* Heat-map grid */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 className="display" style={{ fontSize: "1.25rem", marginBottom: "0.25rem" }}>
          Ástand per {headerDate}
        </h2>
        <p
          style={{
            fontSize: "0.82rem",
            color: "var(--vm-ink-muted)",
            margin: "0 0 0.75rem",
          }}
        >
          {mode === "quarterly"
            ? "Ársfjórðungsleg regime-lesning — stöðugri fyrir lítil segment."
            : "Mánaðarlegt smoothed regime (z₃v₁₂ ± 0,5). Reiti með n < 50 eru birt sem ársfjórðungsleg fallback."}
        </p>
        <div
          style={{
            overflowX: "auto",
            border: "1px solid var(--vm-border)",
            borderRadius: 8,
            background: "var(--vm-surface-elevated)",
          }}
        >
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "0.9rem",
            }}
          >
            <thead>
              <tr style={{ background: "var(--vm-surface)" }}>
                <th style={thStyle} />
                {REGIONS.map((r) => (
                  <th key={r} style={thStyle}>
                    {REGION_LABEL[r]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SEGMENTS.map((seg) => (
                <tr
                  key={seg}
                  style={{ borderTop: "1px solid var(--vm-border)" }}
                >
                  <td
                    style={{
                      padding: "0.6rem 0.85rem",
                      fontWeight: 500,
                      color: "var(--vm-ink)",
                    }}
                  >
                    {formatSegment(seg)}
                  </td>
                  {REGIONS.map((reg) => {
                    const r = cellAt(seg, reg, selectedMonth);
                    const bucket =
                      mode === "quarterly"
                        ? r?.quarterly_regime
                        : r?.display_regime;
                    const isFallback =
                      mode === "monthly" &&
                      r?.regime_source === "quarterly_fallback";
                    const key = `${seg}|${reg}`;
                    const isOpen = openCell === key;
                    return (
                      <td
                        key={reg}
                        style={{
                          padding: "0.6rem 0.85rem",
                          position: "relative",
                          verticalAlign: "top",
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => setOpenCell(isOpen ? null : key)}
                          aria-expanded={isOpen}
                          className={`vm-badge ${pillClass(bucket)}`}
                          style={{
                            border: "none",
                            background: bucket
                              ? undefined
                              : "rgba(138,138,122,0.06)",
                            color: bucket ? undefined : "var(--vm-ink-faint)",
                            cursor: r ? "pointer" : "default",
                            fontSize: "0.78rem",
                          }}
                          disabled={!r}
                        >
                          {pillLabel(bucket)}
                        </button>
                        {isFallback && bucket && (
                          <span
                            title={"Mánaðartölur eru ekki áreiðanlegar fyrir þetta segment (n<50). Sýnir ársfjórðungslegt mat í staðinn."}
                            style={{
                              display: "inline-block",
                              marginLeft: "0.35rem",
                              fontSize: "0.68rem",
                              color: "var(--vm-ink-faint)",
                              fontStyle: "italic",
                            }}
                          >
                            ársfj.
                          </span>
                        )}
                        {isOpen && r && (
                          <CellPopover
                            cellRows={byCell.get(key) || []}
                            segment={seg}
                            region={reg}
                            selectedMonth={selectedMonth}
                            mode={mode}
                            onClose={() => setOpenCell(null)}
                          />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Above-list pooled timeline */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 className="display" style={{ fontSize: "1.25rem", marginBottom: "0.25rem" }}>
          Yfirboð yfir tíma
        </h2>
        <p style={{ fontSize: "0.85rem", color: "var(--vm-ink-muted)", marginBottom: "0.75rem" }}>
          Pooled yfir main residential cells. Gögn enda{" "}
          {allMonths.length ? formatMonth(allMonths[allMonths.length - 1]) : "—"} vegna
          scrape-gap frá júlí 2025 — gula borðið hér að neðan markar gap-tímabilið.
        </p>
        <PoolMonthlyTimeline
          rows={pooledAboveList}
          selectedMonth={selectedMonth}
          allMonths={allMonths}
        />
      </section>
    </>
  );
}

const thStyle = {
  padding: "0.6rem 0.85rem",
  textAlign: "left",
  fontWeight: 600,
  color: "var(--vm-ink-muted)",
  fontSize: "0.75rem",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};
