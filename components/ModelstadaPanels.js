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
  Legend,
} from "recharts";
import { formatSegment } from "@/lib/format";

// DASHBOARD_SPEC_v1 §6 — four /modelstada panels. Client component because
// Recharts hydrates here; page.js passes server-fetched data in as props.

// ── Shared helpers ─────────────────────────────────────────────────────────
const STATUS_LABEL_MAP = {
  ok: "Í lagi",
  caveat: "Með athugasemd",
  wavering: "Sveiflast",
  broken: "Þarfnast skoðunar",
};
const STATUS_COLOR_MAP = {
  ok: "var(--vm-success)",
  caveat: "var(--vm-accent-soft)",
  wavering: "var(--vm-hot)",
  broken: "var(--vm-danger)",
};

function fmtPeriodAxis(p) {
  if (!p) return "";
  const [year, month] = p.split("-");
  const names = ["jan", "feb", "mar", "apr", "maí", "jún", "júl", "ágú", "sep", "okt", "nóv", "des"];
  return `${names[Number(month) - 1]} ${year.slice(2)}`;
}
function fmtPct(v, digits = 1) {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(Number(v) * 100).toFixed(digits).replace(".", ",")} %`;
}

// ── Panel 1 — Held MAPE trend ──────────────────────────────────────────────
export function HeldMapePanel({ history }) {
  const data = useMemo(() => {
    return history
      .filter((r) => r.segment === "RESIDENTIAL_EX_SUMMER" && r.mape != null)
      .sort((a, b) => a.period.localeCompare(b.period))
      .map((r) => ({ period: r.period, mape: Number(r.mape), n_held: r.n_held }));
  }, [history]);

  const latest = data[data.length - 1];
  const yCap = Math.max(0.1, ...data.map((d) => Number(d.mape) || 0));

  return (
    <div className="vm-card" style={{ marginBottom: "1.5rem" }}>
      <p
        style={{
          fontSize: "0.75rem",
          color: "var(--vm-ink-faint)",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          margin: 0,
        }}
      >
        Held-set MAPE síðustu mánuði
      </p>
      {latest && (
        <p
          className="display tabular"
          style={{
            fontSize: "1.8rem",
            margin: "0.4rem 0 0.25rem",
            color: "var(--vm-ink)",
          }}
        >
          {fmtPct(latest.mape)}
        </p>
      )}
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 16, right: 16, bottom: 24, left: 0 }}>
            <XAxis
              dataKey="period"
              tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
              axisLine={{ stroke: "var(--vm-border)" }}
              tickLine={false}
              tickFormatter={fmtPeriodAxis}
            />
            <YAxis
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
              tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
              axisLine={{ stroke: "var(--vm-border)" }}
              tickLine={false}
              domain={[0, yCap * 1.2]}
              width={44}
            />
            <Tooltip
              contentStyle={{
                background: "var(--vm-surface-elevated)",
                border: "1px solid var(--vm-border-strong)",
                borderRadius: 6,
                fontSize: "0.82rem",
              }}
              formatter={(v, _, ctx) => [
                `${fmtPct(v)} (N=${ctx.payload.n_held?.toLocaleString("is-IS") ?? "—"})`,
                "MAPE",
              ]}
              labelFormatter={fmtPeriodAxis}
            />
            <Line
              type="monotone"
              dataKey="mape"
              stroke="var(--vm-primary)"
              strokeWidth={2}
              dot={{ r: 3, fill: "var(--vm-primary)" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p
        style={{
          fontSize: "0.82rem",
          color: "var(--vm-ink-muted)",
          lineHeight: 1.5,
          margin: "0.6rem 0 0",
        }}
      >
        Held-set MAPE er mean absolute percentage error á eignum sem módelið
        sá aldrei í þjálfun (RESIDENTIAL_EX_SUMMER pooled). Lægri tala =
        nákvæmari spár.
      </p>
      {data.length < 12 && latest && (
        <p
          style={{
            fontSize: "0.78rem",
            color: "var(--vm-ink-faint)",
            fontStyle: "italic",
            margin: "0.4rem 0 0",
          }}
        >
          Model tracking byrjaði {fmtPeriodAxis(data[0].period)}. Fullt
          12-mánaða sögufall byrjar að fyllast þegar mánaðarlegar snapshots
          eru keyrðar.
        </p>
      )}
    </div>
  );
}

// ── Panel 2 — PI coverage trend ────────────────────────────────────────────
export function CoveragePanel({ history }) {
  const data = useMemo(() => {
    return history
      .filter((r) => r.segment === "RESIDENTIAL_EX_SUMMER" && r.cov80 != null)
      .sort((a, b) => a.period.localeCompare(b.period))
      .map((r) => ({
        period: r.period,
        cov80: Number(r.cov80),
        cov95: Number(r.cov95),
      }));
  }, [history]);
  const latest = data[data.length - 1];

  return (
    <div className="vm-card" style={{ marginBottom: "1.5rem" }}>
      <p
        style={{
          fontSize: "0.75rem",
          color: "var(--vm-ink-faint)",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          margin: 0,
        }}
      >
        Vissubil — empirísk coverage
      </p>
      {latest && (
        <p
          style={{
            fontSize: "0.95rem",
            margin: "0.5rem 0 0.5rem",
            color: "var(--vm-ink-muted)",
          }}
        >
          80 % bil ={" "}
          <span
            className="tabular"
            style={{ color: "var(--vm-ink)", fontWeight: 500 }}
          >
            {fmtPct(latest.cov80)}
          </span>{" "}
          · 95 % bil ={" "}
          <span
            className="tabular"
            style={{ color: "var(--vm-ink)", fontWeight: 500 }}
          >
            {fmtPct(latest.cov95)}
          </span>
        </p>
      )}
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
            <XAxis
              dataKey="period"
              tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
              axisLine={{ stroke: "var(--vm-border)" }}
              tickLine={false}
              tickFormatter={fmtPeriodAxis}
            />
            <YAxis
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
              tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
              axisLine={{ stroke: "var(--vm-border)" }}
              tickLine={false}
              domain={[0.6, 1]}
              width={44}
            />
            <Tooltip
              contentStyle={{
                background: "var(--vm-surface-elevated)",
                border: "1px solid var(--vm-border-strong)",
                borderRadius: 6,
                fontSize: "0.82rem",
              }}
              formatter={(v, k) => [fmtPct(v), k === "cov80" ? "80 %" : "95 %"]}
              labelFormatter={fmtPeriodAxis}
            />
            <Legend
              verticalAlign="top"
              height={24}
              iconType="plainline"
              wrapperStyle={{ fontSize: "0.8rem" }}
              formatter={(v) => (v === "cov80" ? "80 %" : "95 %")}
            />
            <ReferenceLine y={0.8} stroke="var(--vm-ink-faint)" strokeDasharray="3 3" />
            <ReferenceLine y={0.95} stroke="var(--vm-ink-faint)" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="cov80"
              stroke="var(--vm-primary)"
              strokeWidth={2}
              dot={{ r: 3, fill: "var(--vm-primary)" }}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="cov95"
              stroke="var(--vm-accent)"
              strokeWidth={2}
              strokeDasharray="4 3"
              dot={{ r: 3, fill: "var(--vm-accent)" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p
        style={{
          fontSize: "0.82rem",
          color: "var(--vm-ink-muted)",
          lineHeight: 1.5,
          margin: "0.6rem 0 0",
        }}
      >
        Vissubil mælir hvernig spágildi „hvar er raunverð líklega?" stenst.
        Stöng 80 % við 0,80 markið er gott merki; smávægis frávik innan
        ±5 pp er innan statistical noise.
      </p>
    </div>
  );
}

// ── Panel 3 — Per-segment MAPE table ───────────────────────────────────────
export function SegmentTable({ segments }) {
  // segments: rows with non-null segment, excluding RESIDENTIAL_EX_SUMMER
  // (shown as overall). Sort by MAPE ascending (nulls last).
  const rows = useMemo(() => {
    return segments
      .filter((r) => r.segment && r.segment !== "RESIDENTIAL_EX_SUMMER")
      .slice()
      .sort((a, b) => {
        const am = a.mape == null ? Infinity : Number(a.mape);
        const bm = b.mape == null ? Infinity : Number(b.mape);
        return am - bm;
      });
  }, [segments]);

  return (
    <div className="vm-card" style={{ marginBottom: "1.5rem", padding: 0, overflow: "hidden" }}>
      <p
        style={{
          fontSize: "0.75rem",
          color: "var(--vm-ink-faint)",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          margin: 0,
          padding: "1.25rem 1.5rem 0.85rem",
        }}
      >
        Per-segment MAPE
      </p>
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.92rem",
          }}
        >
          <thead>
            <tr style={{ background: "var(--vm-surface)" }}>
              {["Segment", "MAPE", "N", "Staða"].map((h, i) => (
                <th
                  key={h}
                  style={{
                    textAlign: i >= 1 && i <= 2 ? "right" : "left",
                    padding: "0.55rem 1.5rem",
                    fontWeight: 600,
                    color: "var(--vm-ink-muted)",
                    fontSize: "0.75rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    borderBottom: "1px solid var(--vm-border)",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const lbl = STATUS_LABEL_MAP[r.status_label] ?? r.status_label;
              const color = STATUS_COLOR_MAP[r.status_label] ?? "var(--vm-ink-muted)";
              return (
                <tr key={r.segment} style={{ borderTop: "1px solid var(--vm-border)" }}>
                  <td style={{ padding: "0.55rem 1.5rem", color: "var(--vm-ink)" }}>
                    {formatSegment(r.segment)}
                  </td>
                  <td
                    className="tabular"
                    style={{
                      padding: "0.55rem 1.5rem",
                      textAlign: "right",
                      color: "var(--vm-ink)",
                    }}
                  >
                    {r.mape == null
                      ? "—"
                      : `${(Number(r.mape) * 100).toFixed(1).replace(".", ",")} %`}
                  </td>
                  <td
                    className="tabular"
                    style={{
                      padding: "0.55rem 1.5rem",
                      textAlign: "right",
                      color: "var(--vm-ink-muted)",
                    }}
                  >
                    {r.n_held?.toLocaleString("is-IS") ?? "—"}
                  </td>
                  <td style={{ padding: "0.55rem 1.5rem", color: "var(--vm-ink)" }}>
                    <span
                      aria-hidden
                      style={{
                        display: "inline-block",
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: color,
                        marginRight: 8,
                      }}
                    />
                    {lbl}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p
        style={{
          fontSize: "0.82rem",
          color: "var(--vm-ink-muted)",
          lineHeight: 1.5,
          padding: "0.85rem 1.5rem 1.25rem",
          margin: 0,
        }}
      >
        MAPE varierar milli eignaflokka. Apartments (APT_STANDARD, APT_FLOOR)
        hafa lægstu skekkjuna — stærsta N í þjálfunarsafn og einsleitari
        segment. Einbýli og sumarhús eru snúnari. SUMMERHOUSE er þekkt
        vandamál sem iter5 mun leysa.
      </p>
    </div>
  );
}

// ── Panel 4 — Pipeline health ──────────────────────────────────────────────
export function PipelineHealthPanel({ health }) {
  // health: pre-built array of { key, label, status ('ok'|'warn'|'fail'), detail }
  const icon = (status) => {
    if (status === "warn") return { glyph: "⚠", color: "var(--vm-accent)" };
    if (status === "fail") return { glyph: "✗", color: "var(--vm-danger)" };
    return { glyph: "✓", color: "var(--vm-success)" };
  };

  return (
    <div className="vm-card" style={{ marginBottom: "1.5rem" }}>
      <p
        style={{
          fontSize: "0.75rem",
          color: "var(--vm-ink-faint)",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          margin: 0,
        }}
      >
        Pipeline staða
      </p>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: "0.75rem 0 0",
          display: "flex",
          flexDirection: "column",
          gap: "0.4rem",
        }}
      >
        {health.map((h) => {
          const { glyph, color } = icon(h.status);
          return (
            <li
              key={h.key}
              style={{
                display: "grid",
                gridTemplateColumns: "1.25rem 1fr auto",
                alignItems: "baseline",
                gap: "0.65rem",
                fontSize: "0.88rem",
                color: "var(--vm-ink)",
              }}
            >
              <span aria-hidden style={{ color }}>{glyph}</span>
              <span>{h.label}</span>
              <span
                className="tabular"
                style={{
                  fontSize: "0.8rem",
                  color: "var(--vm-ink-muted)",
                }}
              >
                {h.detail}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
