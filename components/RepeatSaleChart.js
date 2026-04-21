"use client";

import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { formatSegment } from "@/lib/format";

const SEGMENTS = [
  { code: "ALL", label: "Allt (meðalvegið)" },
  { code: "APT_FLOOR", label: "Íbúð á hæð" },
  { code: "APT_STANDARD", label: "Íbúð" },
  { code: "SFH_DETACHED", label: "Einbýli" },
  { code: "ROW_HOUSE", label: "Raðhús" },
];
const REGIONS = [
  { code: "ALL", label: "Allt Ísland" },
  { code: "RVK_core", label: "Reykjavík miðja" },
  { code: "Capital_sub", label: "Höfuðborgarsvæðið" },
  { code: "Country", label: "Landsbyggðin" },
];
const RANGES = [
  { label: "5 ár", years: 5 },
  { label: "10 ár", years: 10 },
  { label: "Allt", years: null },
];

export default function RepeatSaleChart({ series }) {
  const [seg, setSeg] = useState("ALL");
  const [region, setRegion] = useState("ALL");
  const [range, setRange] = useState("5 ár");

  const data = useMemo(() => {
    const filtered = series.filter((r) => {
      if (seg !== "ALL" && r.canonical_code !== seg) return false;
      if (region !== "ALL" && r.region_tier !== region) return false;
      return true;
    });

    // Aggregate by period across segments/regions if ALL chosen
    const byPeriod = new Map();
    filtered.forEach((r) => {
      if (!byPeriod.has(r.period)) {
        byPeriod.set(r.period, {
          period: r.period,
          year: r.year,
          quarter: r.quarter,
          real_sum: 0,
          nominal_sum: 0,
          weight: 0,
        });
      }
      const entry = byPeriod.get(r.period);
      const w = r.n_pairs_in_period || 1;
      entry.real_sum += (r.index_value_real || 0) * w;
      entry.nominal_sum += (r.index_value_nominal || 0) * w;
      entry.weight += w;
    });
    let arr = Array.from(byPeriod.values())
      .map((e) => ({
        period: e.period,
        year: e.year,
        quarter: e.quarter,
        real: e.weight ? e.real_sum / e.weight : null,
        nominal: e.weight ? e.nominal_sum / e.weight : null,
      }))
      .sort((a, b) => a.year - b.year || a.quarter - b.quarter);

    const rangeDef = RANGES.find((r) => r.label === range);
    if (rangeDef?.years) {
      const maxYear = arr.length ? arr[arr.length - 1].year : 2026;
      const minYear = maxYear - rangeDef.years;
      arr = arr.filter((d) => d.year >= minYear);
    }
    return arr;
  }, [series, seg, region, range]);

  return (
    <div className="vm-card vm-card-elevated" style={{ padding: "1.5rem" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem 1.5rem",
          marginBottom: "1.5rem",
          alignItems: "center",
        }}
      >
        <Select
          label="Segment"
          value={seg}
          onChange={setSeg}
          options={SEGMENTS.map((s) => ({ value: s.code, label: s.label }))}
        />
        <Select
          label="Svæði"
          value={region}
          onChange={setRegion}
          options={REGIONS.map((r) => ({ value: r.code, label: r.label }))}
        />
        <div style={{ display: "flex", gap: "0.5rem", marginLeft: "auto" }}>
          {RANGES.map((r) => (
            <button
              key={r.label}
              onClick={() => setRange(r.label)}
              className={range === r.label ? "vm-btn" : "vm-btn-secondary"}
              style={{ padding: "0.4rem 0.85rem", fontSize: "0.85rem" }}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div style={{ width: "100%", height: 420 }}>
        <ResponsiveContainer>
          <LineChart
            data={data}
            margin={{ top: 10, right: 20, bottom: 10, left: 0 }}
          >
            <CartesianGrid stroke="#e3d9c5" strokeDasharray="3 3" />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 11, fill: "#526375" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#526375" }}
              domain={["dataMin - 5", "dataMax + 5"]}
              tickFormatter={(v) => Math.round(v)}
            />
            <Tooltip
              contentStyle={{
                background: "#fbf7ef",
                border: "1px solid #c9bca2",
                borderRadius: 6,
                fontSize: "0.85rem",
              }}
              formatter={(v) => (v == null ? "—" : Number(v).toFixed(1))}
            />
            <Legend verticalAlign="top" height={36} />
            <Line
              name="Raun (CPI-deflated)"
              dataKey="real"
              stroke="#1f3a5f"
              strokeWidth={2.5}
              dot={false}
              connectNulls
            />
            <Line
              name="Nominal"
              dataKey="nominal"
              stroke="#c87146"
              strokeWidth={1.75}
              strokeDasharray="5 5"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div
        style={{
          marginTop: "1rem",
          fontSize: "0.82rem",
          color: "var(--vm-ink-faint)",
        }}
      >
        Gildið 100 samsvarar 2006Q2. Vegið yfir {data.length || 0} fjórðunga.
      </div>
    </div>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label
      style={{
        display: "flex",
        gap: "0.5rem",
        alignItems: "center",
        fontSize: "0.88rem",
        color: "var(--vm-ink-muted)",
      }}
    >
      <span>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          padding: "0.45rem 0.7rem",
          background: "var(--vm-surface)",
          border: "1px solid var(--vm-border-strong)",
          borderRadius: 6,
          fontFamily: "var(--font-body)",
          fontSize: "0.88rem",
          color: "var(--vm-ink)",
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
