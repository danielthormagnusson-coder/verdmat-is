import { formatPercent, formatSegment, heatBucketLabel } from "@/lib/format";

export default function MarketContextCard({ rows, segment, region }) {
  // Pick the "current" regime: prefer neutral row for display; show all three as mini-cards.
  const byBucket = {};
  rows.forEach((r) => (byBucket[r.heat_bucket] = r));

  const regionLabel =
    region === "RVK_core"
      ? "Reykjavík miðja"
      : region === "Capital_sub"
      ? "Höfuðborgarsvæðið"
      : region === "Country"
      ? "Landsbyggðin"
      : region;

  return (
    <div className="vm-card vm-card-elevated">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "0.95rem",
              color: "var(--vm-ink-muted)",
              marginBottom: "0.15rem",
            }}
          >
            Markaðssegment
          </div>
          <div
            className="display"
            style={{ fontSize: "1.35rem", fontWeight: 500 }}
          >
            {formatSegment(segment)} · {regionLabel}
          </div>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "1rem",
        }}
      >
        {["hot", "neutral", "cold"].map((bucket) => {
          const row = byBucket[bucket];
          if (!row) return null;
          const cls =
            bucket === "hot"
              ? "vm-badge-hot"
              : bucket === "cold"
              ? "vm-badge-cold"
              : "vm-badge-neutral";
          return (
            <div
              key={bucket}
              style={{
                padding: "1rem",
                background: "var(--vm-surface)",
                borderRadius: 8,
                border: "1px solid var(--vm-border)",
              }}
            >
              <span className={`vm-badge ${cls}`} style={{ marginBottom: 8 }}>
                {heatBucketLabel(bucket)}
              </span>
              <div
                style={{
                  marginTop: "0.6rem",
                  fontSize: "0.82rem",
                  color: "var(--vm-ink-muted)",
                  marginBottom: "0.15rem",
                }}
              >
                Yfir ásettu verði
              </div>
              <div
                className="tabular"
                style={{ fontWeight: 500, fontSize: "1.1rem" }}
              >
                {formatPercent(row.above_list_rate, 1)}
              </div>
              <div
                style={{
                  fontSize: "0.78rem",
                  color: "var(--vm-ink-faint)",
                  marginTop: "0.25rem",
                }}
              >
                n={Math.round(row.n_pairs)} pör
              </div>
            </div>
          );
        })}
      </div>
      <div
        style={{
          marginTop: "1rem",
          fontSize: "0.82rem",
          color: "var(--vm-ink-faint)",
        }}
      >
        ATS-heat byggt á hlutfalli sala yfir ásettu verði síðustu 5 fjórðungum.
      </div>
    </div>
  );
}
