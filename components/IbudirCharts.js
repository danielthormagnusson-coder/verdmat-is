"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  CartesianGrid,
  Legend,
} from "recharts";
import { formatSegment } from "@/lib/format";

// DASHBOARD_SPEC_v1 §5 — five LLM-derived aggregate charts. Metric 5
// (orðatíðni) is deferred to v1.1 per §5.1; this file ships the other five.
//
// Bug 7 fix (2026-04-27): all per-(segment × quarter) aggregates drop cells
// where the metric's denominator is below MIN_N_PER_CELL. Without this,
// post-2025-07 scrape-gap quarters with n=2-5 produced spurious 40%+ spikes
// or step-down drops on the Einbýli/Raðhús lines. Simpler than the regime
// quarterly-fallback used on /markadsstada — for aggregate trends a shorter
// line is acceptable. Disclosure footnote shows on each affected chart.
const MIN_N_PER_CELL = 30;
const MIN_N_DISCLOSURE =
  "Punktum sleppt þar sem n<30 (þunn gögn í scrape-gap).";

const HEADLINE_SEGS = ["APT_STANDARD", "SFH_DETACHED", "ROW_HOUSE"];
const APT_SEGS_FOR_SERLOD = ["APT_FLOOR", "APT_STANDARD"];
const SEG_COLOR = {
  APT_STANDARD: "var(--vm-primary)",
  APT_FLOOR: "var(--vm-primary)",
  SFH_DETACHED: "var(--vm-accent)",
  ROW_HOUSE: "var(--vm-success)",
  APT_BASEMENT: "var(--vm-ink-muted)",
  APT_ATTIC: "var(--vm-ink-faint)",
  SEMI_DETACHED: "var(--vm-cold)",
  SUMMERHOUSE: "var(--vm-hot)",
};
const REGIONS = ["RVK_core", "Capital_sub", "Country"];
const REGION_LABEL = {
  RVK_core: "Reykjavík miðja",
  Capital_sub: "Höfuðborgarsvæðið",
  Country: "Landsbyggðin",
};

const FRAMING_KEYS = [
  { key: "pct_framing_terse", label: "Hófstillt" },
  { key: "pct_framing_standard", label: "Stöðluð" },
  { key: "pct_framing_elaborate", label: "Ítarleg" },
  { key: "pct_framing_promotional", label: "Söluhrifið" },
];
const FRAMING_COLOR = {
  pct_framing_terse: "var(--vm-cold)",
  pct_framing_standard: "var(--vm-primary)",
  pct_framing_elaborate: "var(--vm-success)",
  pct_framing_promotional: "var(--vm-hot)",
};

function periodToSort(p) {
  // "2023Q2" → 2023*4 + 2 = sort key
  const m = /^(\d{4})Q([1-4])$/.exec(p || "");
  if (!m) return 0;
  return Number(m[1]) * 4 + Number(m[2]);
}
const sortByPeriod = (a, b) => periodToSort(a.period) - periodToSort(b.period);
const yearOnly = (p) => (p && p.length >= 4 ? p.slice(0, 4) : p);

function pivotTimeSeries(rows, valueKey, segments, nKey = null) {
  // Pivot to {period, [seg]: val}; drop a (segment × period) cell when the
  // metric's per-cell n falls below MIN_N_PER_CELL. Resulting line will end
  // earlier for thin segments but never spike on n=2-5 outliers.
  const byPeriod = new Map();
  for (const r of rows) {
    if (!segments.includes(r.canonical_code)) continue;
    if (r[valueKey] == null) continue;
    if (nKey && r[nKey] != null && Number(r[nKey]) < MIN_N_PER_CELL) continue;
    if (!byPeriod.has(r.period))
      byPeriod.set(r.period, { period: r.period });
    byPeriod.get(r.period)[r.canonical_code] = Number(r[valueKey]);
  }
  return Array.from(byPeriod.values()).sort(sortByPeriod);
}

function ChartNote({ children }) {
  return (
    <p
      style={{
        fontSize: "0.75rem",
        color: "var(--vm-ink-faint)",
        fontStyle: "italic",
        marginTop: "0.4rem",
        marginBottom: 0,
        lineHeight: 1.4,
      }}
    >
      {children}
    </p>
  );
}

function pctFormatter(v, digits = 0) {
  if (v == null) return "—";
  return `${(Number(v) * 100).toFixed(digits).replace(".", ",")} %`;
}

function Tooltip3Series({ active, payload, label, valueKey, formatValue }) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div
      style={{
        background: "var(--vm-surface-elevated)",
        border: "1px solid var(--vm-border-strong)",
        borderRadius: 6,
        padding: "0.5rem 0.75rem",
        fontSize: "0.82rem",
        color: "var(--vm-ink)",
        fontFamily: "var(--font-body)",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: "0.2rem" }}>{label}</div>
      {payload.map((p) =>
        p.value == null ? null : (
          <div
            key={p.dataKey}
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: "0.75rem",
              color: p.color,
            }}
          >
            <span>{formatSegment(p.dataKey)}</span>
            <span className="tabular">{formatValue(p.value)}</span>
          </div>
        ),
      )}
    </div>
  );
}

// ── Metric 1 ──────────────────────────────────────────────────────────────
export function ConditionChart({ pooled }) {
  const data = useMemo(
    () =>
      pivotTimeSeries(
        pooled,
        "mean_interior_condition_score",
        HEADLINE_SEGS,
        "n_listings_condition",
      ),
    [pooled],
  );
  return (
    <>
    <div style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
          <XAxis
            dataKey="period"
            tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
            tickFormatter={yearOnly}
            interval={3}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
            domain={["auto", "auto"]}
            tickFormatter={(v) => Number(v).toFixed(1).replace(".", ",")}
            width={36}
          />
          <Tooltip
            content={(p) => (
              <Tooltip3Series
                {...p}
                formatValue={(v) => Number(v).toFixed(2).replace(".", ",")}
              />
            )}
            cursor={{ stroke: "var(--vm-border-strong)" }}
          />
          <Legend
            verticalAlign="top"
            height={28}
            iconType="plainline"
            wrapperStyle={{ fontSize: "0.8rem", fontFamily: "var(--font-body)" }}
            formatter={(v) => formatSegment(v)}
          />
          {HEADLINE_SEGS.map((s) => (
            <Line
              key={s}
              type="monotone"
              dataKey={s}
              stroke={SEG_COLOR[s]}
              strokeWidth={2}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
    <ChartNote>{MIN_N_DISCLOSURE}</ChartNote>
    </>
  );
}

// ── Metric 2 ──────────────────────────────────────────────────────────────
export function RenovationChart({ pooled }) {
  const data = useMemo(
    () =>
      pivotTimeSeries(
        pooled,
        "pct_recently_renovated",
        HEADLINE_SEGS,
        "n_listings_renovation",
      ),
    [pooled],
  );
  return (
    <>
    <div style={{ width: "100%", height: 240 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
          <XAxis
            dataKey="period"
            tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
            tickFormatter={yearOnly}
            interval={3}
          />
          <YAxis
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
            domain={[0, "auto"]}
            width={40}
          />
          <Tooltip
            content={(p) => (
              <Tooltip3Series {...p} formatValue={(v) => pctFormatter(v, 1)} />
            )}
            cursor={{ stroke: "var(--vm-border-strong)" }}
          />
          <Legend
            verticalAlign="top"
            height={28}
            iconType="plainline"
            wrapperStyle={{ fontSize: "0.8rem", fontFamily: "var(--font-body)" }}
            formatter={(v) => formatSegment(v)}
          />
          {HEADLINE_SEGS.map((s) => (
            <Line
              key={s}
              type="monotone"
              dataKey={s}
              stroke={SEG_COLOR[s]}
              strokeWidth={2}
              dot={false}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
    <ChartNote>{MIN_N_DISCLOSURE}</ChartNote>
    </>
  );
}

// ── Metric 3 ──────────────────────────────────────────────────────────────
export function UnregisteredBarChart({ perRegion }) {
  // Aggregate weighted across periods, but skip a (region × segment × period)
  // contribution if its n is below MIN_N_PER_CELL — Bug 7 fix prevents thin
  // post-gap quarters from polluting the rolled-up bar.
  const data = useMemo(() => {
    const byRegSeg = new Map();
    for (const r of perRegion) {
      if (!REGIONS.includes(r.region_tier)) continue;
      if (!HEADLINE_SEGS.includes(r.canonical_code)) continue;
      if (r.pct_has_unregistered_space == null) continue;
      const n = Number(r.n_listings_unregistered) || 0;
      if (n < MIN_N_PER_CELL) continue;
      const k = `${r.region_tier}|${r.canonical_code}`;
      if (!byRegSeg.has(k))
        byRegSeg.set(k, { weighted: 0, total: 0 });
      const agg = byRegSeg.get(k);
      agg.weighted += Number(r.pct_has_unregistered_space) * n;
      agg.total += n;
    }
    const byRegion = new Map();
    for (const [k, { weighted, total }] of byRegSeg) {
      const [reg, seg] = k.split("|");
      if (total === 0) continue;
      if (!byRegion.has(reg))
        byRegion.set(reg, { region: REGION_LABEL[reg] || reg });
      byRegion.get(reg)[seg] = weighted / total;
    }
    return REGIONS.map((r) => byRegion.get(r)).filter(Boolean);
  }, [perRegion]);

  return (
    <>
    <div style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
          <XAxis
            dataKey="region"
            tick={{ fontSize: 11, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
            domain={[0, "auto"]}
            width={40}
          />
          <CartesianGrid vertical={false} stroke="var(--vm-border)" />
          <Tooltip
            contentStyle={{
              background: "var(--vm-surface-elevated)",
              border: "1px solid var(--vm-border-strong)",
              borderRadius: 6,
              fontSize: "0.82rem",
            }}
            formatter={(v, k) => [pctFormatter(v, 1), formatSegment(k)]}
          />
          <Legend
            verticalAlign="top"
            height={28}
            iconType="square"
            wrapperStyle={{ fontSize: "0.8rem", fontFamily: "var(--font-body)" }}
            formatter={(v) => formatSegment(v)}
          />
          {HEADLINE_SEGS.map((s) => (
            <Bar key={s} dataKey={s} fill={SEG_COLOR[s]} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
    <ChartNote>
      Tölurnar pool-a yfir öll ársfjórðungs-tímabil 2018+. Reitir með n &lt; 30
      eru sleppt til að forðast skekkju frá þunnum scrape-gap mánuðum.
    </ChartNote>
    </>
  );
}

// ── Metric 4 ──────────────────────────────────────────────────────────────
export function SerlodSmallMultiples({ perRegion }) {
  // Per region, line chart of pct_apt_with_serlod over time for APT segments.
  // Bug 7: drop (region × segment × quarter) cells where n_listings_serlod < 30
  // so a thin scrape-gap quarter doesn't spike one of the small-multiple lines.
  const byRegion = useMemo(() => {
    const map = new Map();
    for (const r of perRegion) {
      if (!REGIONS.includes(r.region_tier)) continue;
      if (!APT_SEGS_FOR_SERLOD.includes(r.canonical_code)) continue;
      if (r.pct_apt_with_serlod == null) continue;
      if (
        r.n_listings_serlod != null &&
        Number(r.n_listings_serlod) < MIN_N_PER_CELL
      )
        continue;
      if (!map.has(r.region_tier)) map.set(r.region_tier, new Map());
      const inner = map.get(r.region_tier);
      if (!inner.has(r.period))
        inner.set(r.period, { period: r.period });
      inner.get(r.period)[r.canonical_code] = Number(r.pct_apt_with_serlod);
    }
    return REGIONS.map((reg) => ({
      region: reg,
      data: Array.from((map.get(reg) || new Map()).values()).sort(sortByPeriod),
    }));
  }, [perRegion]);

  return (
    <>
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "1rem",
      }}
    >
      {byRegion.map(({ region, data }) => (
        <div
          key={region}
          className="vm-card"
          style={{ padding: "0.85rem 1rem" }}
        >
          <p
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "var(--vm-ink-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              margin: "0 0 0.4rem",
            }}
          >
            {REGION_LABEL[region]}
          </p>
          <div style={{ width: "100%", height: 140 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 4, right: 4, bottom: 16, left: 0 }}>
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 9, fill: "var(--vm-ink-faint)" }}
                  axisLine={{ stroke: "var(--vm-border)" }}
                  tickLine={false}
                  tickFormatter={yearOnly}
                  interval="preserveStartEnd"
                />
                <YAxis
                  hide
                  domain={[0, "auto"]}
                />
                <Tooltip
                  contentStyle={{
                    background: "var(--vm-surface-elevated)",
                    border: "1px solid var(--vm-border-strong)",
                    borderRadius: 6,
                    fontSize: "0.78rem",
                  }}
                  formatter={(v, k) => [pctFormatter(v, 1), formatSegment(k)]}
                />
                {APT_SEGS_FOR_SERLOD.map((s) => (
                  <Line
                    key={s}
                    type="monotone"
                    dataKey={s}
                    stroke={SEG_COLOR[s]}
                    strokeWidth={1.8}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
    </div>
    <ChartNote>{MIN_N_DISCLOSURE}</ChartNote>
    </>
  );
}

// ── Metric 6 (framing) — stacked area per pooled APT_STANDARD ─────────────
export function FramingStackedArea({ pooled }) {
  const data = useMemo(() => {
    return pooled
      .filter((r) => r.canonical_code === "APT_STANDARD")
      .filter((r) => r.pct_framing_standard != null)
      .filter(
        (r) =>
          r.n_listings_total == null ||
          Number(r.n_listings_total) >= MIN_N_PER_CELL,
      )
      .map((r) => ({
        period: r.period,
        pct_framing_terse: Number(r.pct_framing_terse || 0),
        pct_framing_standard: Number(r.pct_framing_standard || 0),
        pct_framing_elaborate: Number(r.pct_framing_elaborate || 0),
        pct_framing_promotional: Number(r.pct_framing_promotional || 0),
      }))
      .sort(sortByPeriod);
  }, [pooled]);
  return (
    <>
    <div style={{ width: "100%", height: 260 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
          <XAxis
            dataKey="period"
            tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
            tickFormatter={yearOnly}
            interval={3}
          />
          <YAxis
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            tick={{ fontSize: 10, fill: "var(--vm-ink-muted)" }}
            axisLine={{ stroke: "var(--vm-border)" }}
            tickLine={false}
            domain={[0, 1]}
            width={40}
          />
          <Tooltip
            contentStyle={{
              background: "var(--vm-surface-elevated)",
              border: "1px solid var(--vm-border-strong)",
              borderRadius: 6,
              fontSize: "0.82rem",
            }}
            formatter={(v, k) => {
              const lbl = FRAMING_KEYS.find((f) => f.key === k)?.label ?? k;
              return [pctFormatter(v, 1), lbl];
            }}
          />
          <Legend
            verticalAlign="top"
            height={28}
            iconType="square"
            wrapperStyle={{ fontSize: "0.8rem", fontFamily: "var(--font-body)" }}
            formatter={(v) =>
              FRAMING_KEYS.find((f) => f.key === v)?.label ?? v
            }
          />
          {FRAMING_KEYS.map(({ key }) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stackId="1"
              stroke={FRAMING_COLOR[key]}
              fill={FRAMING_COLOR[key]}
              fillOpacity={0.75}
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
    <ChartNote>{MIN_N_DISCLOSURE}</ChartNote>
    </>
  );
}
