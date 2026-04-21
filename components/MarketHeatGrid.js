import { formatPercent, formatSegment, heatBucketLabel } from "@/lib/format";

const SEGMENTS = [
  "APT_FLOOR",
  "APT_STANDARD",
  "SFH_DETACHED",
  "ROW_HOUSE",
  "SEMI_DETACHED",
  "SUMMERHOUSE",
];
const REGIONS = ["RVK_core", "Capital_sub", "Country"];
const REGION_LABEL = {
  RVK_core: "Reykjavík miðja",
  Capital_sub: "Höfuðborgarsvæðið",
  Country: "Landsbyggðin",
};

export default function MarketHeatGrid({ rows }) {
  // Pool across heat_buckets: pick the bucket with the most recent pooled data;
  // show above_list_rate of the *hot* row as the "heat" indicator for display.
  // Fallback: max above_list_rate across all buckets.
  const bySegReg = {};
  rows.forEach((r) => {
    const key = `${r.canonical_code}|${r.region_tier}`;
    if (!bySegReg[key]) bySegReg[key] = {};
    bySegReg[key][r.heat_bucket] = r;
  });

  return (
    <div className="vm-card vm-card-elevated" style={{ padding: "1.75rem" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `180px repeat(${REGIONS.length}, 1fr)`,
          gap: "0.75rem",
          alignItems: "center",
        }}
      >
        <div />
        {REGIONS.map((r) => (
          <div
            key={r}
            style={{
              textAlign: "center",
              fontSize: "0.82rem",
              color: "var(--vm-ink-muted)",
              fontWeight: 600,
              letterSpacing: "0.05em",
              textTransform: "uppercase",
            }}
          >
            {REGION_LABEL[r]}
          </div>
        ))}
        {SEGMENTS.map((seg) => (
          <Row
            key={seg}
            seg={seg}
            regions={REGIONS}
            bySegReg={bySegReg}
          />
        ))}
      </div>
    </div>
  );
}

function Row({ seg, regions, bySegReg }) {
  return (
    <>
      <div style={{ fontWeight: 500, color: "var(--vm-ink)" }}>
        {formatSegment(seg)}
      </div>
      {regions.map((reg) => {
        const cell = bySegReg[`${seg}|${reg}`];
        if (!cell) {
          return <Cell key={reg} empty />;
        }
        // Pick highest above_list_rate bucket for display
        const buckets = Object.values(cell);
        const top = buckets.reduce((a, b) =>
          (b.above_list_rate || 0) > (a.above_list_rate || 0) ? b : a
        );
        return <Cell key={reg} row={top} />;
      })}
    </>
  );
}

function Cell({ row, empty }) {
  if (empty) {
    return (
      <div
        style={{
          padding: "0.75rem 1rem",
          background: "var(--vm-surface)",
          borderRadius: 8,
          textAlign: "center",
          color: "var(--vm-ink-faint)",
          fontSize: "0.85rem",
        }}
      >
        —
      </div>
    );
  }
  const cls =
    row.heat_bucket === "hot"
      ? "vm-badge-hot"
      : row.heat_bucket === "cold"
      ? "vm-badge-cold"
      : "vm-badge-neutral";
  return (
    <div
      style={{
        padding: "0.85rem 1rem",
        background: "var(--vm-surface)",
        borderRadius: 8,
        textAlign: "center",
      }}
    >
      <span className={`vm-badge ${cls}`} style={{ marginBottom: 6 }}>
        {heatBucketLabel(row.heat_bucket)}
      </span>
      <div
        className="tabular"
        style={{ marginTop: "0.4rem", fontWeight: 500 }}
      >
        {formatPercent(row.above_list_rate, 1)}
      </div>
      <div
        style={{
          fontSize: "0.72rem",
          color: "var(--vm-ink-faint)",
          marginTop: "0.15rem",
        }}
      >
        n={Math.round(row.n_pairs || 0)}
      </div>
    </div>
  );
}
