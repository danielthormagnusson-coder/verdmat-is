// Spec §2.2 — A+B hybrid hero. Server component, pure render.

function formatSignedPercent(pct, digits = 1) {
  if (pct == null || Number.isNaN(pct)) return "—";
  const n = Number(pct);
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  const body = Math.abs(n).toFixed(digits).replace(".", ",");
  return `${sign}${body} %`;
}

function pillClassFor(pill) {
  switch (pill) {
    case "HEITUR": return "vm-badge-hot";
    case "KALDUR": return "vm-badge-cold";
    default: return "vm-badge-neutral";
  }
}

export default function MarketHero({ heroA, heroB }) {
  const { pct } = heroA;
  const isPositive = pct != null && pct > 0;
  const isNegative = pct != null && pct < 0;

  const numberColor = isPositive
    ? "var(--vm-success)"
    : isNegative
    ? "var(--vm-danger)"
    : "var(--vm-ink)";

  const pillClass = pillClassFor(heroB.pill);

  return (
    <section style={{ marginTop: "1.5rem", marginBottom: "2rem" }}>
      <p
        style={{
          fontSize: "0.75rem",
          color: "var(--vm-ink-faint)",
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          marginBottom: "1rem",
        }}
      >
        Raunverð íbúða síðustu 12 mánuði
      </p>

      {pct != null ? (
        <div
          className="display tabular"
          style={{
            fontSize: "clamp(4rem, 10vw, 7rem)",
            lineHeight: 0.95,
            color: numberColor,
            marginBottom: "0.75rem",
          }}
        >
          {formatSignedPercent(pct)}
        </div>
      ) : (
        <div
          className="display"
          style={{
            fontSize: "clamp(1.25rem, 2.5vw, 1.6rem)",
            color: "var(--vm-ink-muted)",
            marginBottom: "0.75rem",
          }}
        >
          Ekki tiltæk ennþá
        </div>
      )}

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "0.75rem",
          fontSize: "1.05rem",
          color: "var(--vm-ink-muted)",
          marginBottom: "1.5rem",
        }}
      >
        <span>Markaðurinn er núna</span>
        <span
          className={`vm-badge ${pillClass}`}
          style={{
            fontSize: "0.9rem",
            padding: "0.3rem 0.75rem",
            letterSpacing: "0.08em",
          }}
        >
          {heroB.pill}
        </span>
      </div>

      <p
        style={{
          fontSize: "1.05rem",
          lineHeight: 1.55,
          color: "var(--vm-ink-muted)",
          maxWidth: 720,
        }}
      >
        Íslenski fasteignamarkaðurinn í rauntíma. Verdmat.is samantekur
        kaupsamninga, auglýsingar og markaðsástand yfir 20 ára tímabil til að
        gefa þér nákvæma mynd af hvernig verð hafa þróast. Skoðaðu þróun eftir
        svæði, segmenti og tímabili.
      </p>
    </section>
  );
}
