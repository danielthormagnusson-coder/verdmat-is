import Link from "next/link";
import MarketHero from "@/components/MarketHero";
import MetricsCards from "@/components/MetricsCards";
import SegmentTimelineChart from "@/components/SegmentTimelineChart";
import ScrapeGapBanner from "@/components/ScrapeGapBanner";
import { loadLandingData } from "@/lib/dashboard-queries";

export const revalidate = 600;

export const metadata = {
  title: "Fasteignamarkaðurinn á Íslandi — Verdmat",
  description:
    "Hlutlægt yfirlit yfir íslenska fasteignamarkaðinn: verðvísitala, markaðshiti, söluhraði. Byggt á 226.000+ kaupsamningum og 471.000+ auglýsingum.",
  openGraph: {
    title: "Fasteignamarkaðurinn á Íslandi — Verdmat",
    description:
      "Raunverðs vísitala, markaðshiti og líkansstaða fyrir íslenska fasteignamarkaðinn. Uppfært mánaðarlega, byggt á þinglýstum kaupsamningum.",
    type: "website",
    locale: "is_IS",
  },
  twitter: {
    card: "summary_large_image",
    title: "Fasteignamarkaðurinn á Íslandi",
    description:
      "Raunverðs vísitala, markaðshiti og líkansstaða — uppfært mánaðarlega.",
  },
};

const DRILL_DOWN_LINKS = [
  { label: "Raunverðs vísitala", href: "/markadur/visitala" },
  { label: "Markaðsstaða", href: "/markadur/markadsstada" },
  { label: "Íbúðaástand", href: "/markadur/ibudir" },
  { label: "Líkansstaða", href: "/markadur/modelstada" },
];

export default async function MarketLandingPage() {
  const data = await loadLandingData();

  return (
    <main className="vm-container" style={{ padding: "2.5rem 0 4rem" }}>
      <h1 className="sr-only" style={srOnly}>
        Fasteignamarkaðurinn á Íslandi
      </h1>

      <p
        style={{
          fontSize: "0.75rem",
          color: "var(--vm-accent)",
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          marginBottom: "0.25rem",
        }}
      >
        FASTEIGNAMARKAÐURINN · {data.heroA.currentPeriod ?? "—"}
      </p>

      <MarketHero heroA={data.heroA} heroB={data.heroB} />

      <div style={{ marginBottom: "2rem" }}>
        <ScrapeGapBanner />
      </div>

      <MetricsCards card1={data.card1} card2={data.card2} card3={data.card3} />

      <section style={{ marginBottom: "2.5rem" }}>
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--vm-ink-muted)",
            fontWeight: 500,
            marginBottom: "0.75rem",
          }}
        >
          Raunverðs vísitala eftir segmenti — 2006Q2 = 100
        </p>
        <SegmentTimelineChart data={data.timeline} />
      </section>

      <section style={{ marginBottom: "2.5rem" }}>
        <h2
          className="display"
          style={{ fontSize: "1.3rem", marginBottom: "1rem" }}
        >
          Skoða ítarlega
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "0.75rem",
          }}
        >
          {DRILL_DOWN_LINKS.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className="vm-btn-secondary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.85rem 1.25rem",
                textDecoration: "none",
                fontSize: "0.95rem",
              }}
            >
              <span>{label}</span>
              <span aria-hidden style={{ color: "var(--vm-accent)" }}>→</span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}

const srOnly = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0,0,0,0)",
  whiteSpace: "nowrap",
  border: 0,
};
