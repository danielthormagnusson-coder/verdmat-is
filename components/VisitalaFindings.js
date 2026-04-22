// Spec §3.4 — three publishable-findings cards.
// Numeric anchors taken from Áfangi 6 closure doc per spec.

import Link from "next/link";

function Card({ title, value, body, cta, ctaHref, accent }) {
  return (
    <div
      className="vm-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        minHeight: 180,
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
        ▸ {title}
      </p>
      <p
        className="display tabular"
        style={{
          fontSize: "1.5rem",
          margin: 0,
          color: accent,
          lineHeight: 1.1,
        }}
      >
        {value}
      </p>
      <p
        style={{
          fontSize: "0.9rem",
          color: "var(--vm-ink-muted)",
          margin: 0,
          lineHeight: 1.5,
        }}
      >
        {body}
      </p>
      {cta && ctaHref && (
        <Link
          href={ctaHref}
          style={{
            fontSize: "0.85rem",
            color: "var(--vm-primary)",
            marginTop: "auto",
            paddingTop: "0.4rem",
          }}
        >
          {cta} →
        </Link>
      )}
    </div>
  );
}

export default function VisitalaFindings() {
  return (
    <section style={{ marginTop: "3rem" }}>
      <h2
        className="display"
        style={{ fontSize: "1.4rem", marginBottom: "1rem" }}
      >
        Publishable findings
      </h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "1rem",
        }}
      >
        <Card
          title="Country catch-up"
          value="+74,9 % vs +35,6 %"
          body={"Raunverð á landsbyggðinni hefur hækkað 74,9 % frá 2006 miðað við 35,6 % í Reykjavík miðju. Mestur hluti „catch-up“ gerðist 2020–2024."}
          accent="var(--vm-accent)"
        />
        <Card
          title="ROW_HOUSE RVK niche"
          value="−24 % vs −40 %"
          body="Raðhús í RVK fóru aðra leið en restin: mild crash (~24%) en hraðari recovery og platform frá 2013."
          accent="var(--vm-success)"
        />
        <Card
          title="SUMMERHOUSE missed crash"
          value="+7,0 % CAGR"
          body="Sumarhús á landsbyggðinni misstu 2008-hrunið alveg — counter-cyclical vs innlent eftirspurnarfall."
          accent="var(--vm-hot)"
        />
      </div>
    </section>
  );
}
