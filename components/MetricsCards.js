// Spec §2.3 — 3 secondary metric cards.

function formatSignedPercent(pct, digits = 1) {
  if (pct == null || Number.isNaN(pct)) return "—";
  const n = Number(pct);
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  const body = Math.abs(n).toFixed(digits).replace(".", ",");
  return `${sign}${body} %`;
}

function formatPlainPercent(pct, digits = 1) {
  if (pct == null || Number.isNaN(pct)) return "—";
  return `${Number(pct).toFixed(digits).replace(".", ",")} %`;
}

function Card({ label, value, subtitle }) {
  return (
    <div
      className="vm-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        minHeight: 140,
      }}
    >
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
        {label}
      </p>
      <p
        className="display tabular"
        style={{
          fontSize: "2rem",
          lineHeight: 1.1,
          margin: 0,
          color: "var(--vm-ink)",
        }}
      >
        {value}
      </p>
      <p
        style={{
          fontSize: "0.8rem",
          color: "var(--vm-ink-muted)",
          margin: 0,
        }}
      >
        {subtitle}
      </p>
    </div>
  );
}

export default function MetricsCards({ card1, card2, card3 }) {
  // Card 3 (MAPE) — spec wireframe shows "mán 2026-03" subtitle
  const card3Value = card3?.mape != null
    ? formatPlainPercent(Number(card3.mape) * 100)
    : "—";
  const card3Subtitle = card3?.period
    ? `mán ${card3.period} · residential ex-summer`
    : "fyrsta uppfærsla kemur í maí";

  return (
    <section
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "1rem",
        marginBottom: "2.5rem",
      }}
    >
      <Card
        label="Yfirboð síðustu 3 mánuði"
        value={card1?.pct != null ? formatPlainPercent(card1.pct, 0) : "—"}
        subtitle="main residential, pooled"
      />
      <Card
        label="Raunverðs CAGR síðustu 10 ár"
        value={card2?.pct != null ? formatSignedPercent(card2.pct, 1) : "—"}
        subtitle="main residential, pooled"
      />
      <Card
        label="Líkansgæði (held MAPE)"
        value={card3Value}
        subtitle={card3Subtitle}
      />
    </section>
  );
}
