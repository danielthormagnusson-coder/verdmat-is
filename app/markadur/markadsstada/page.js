import Link from "next/link";
import { supabase } from "@/lib/supabase";
import MarkadsstadaDashboard from "@/components/MarkadsstadaDashboard";
import BackProjectionWidget from "@/components/BackProjectionWidget";

export const revalidate = 600;

export const metadata = {
  title: "Markaðsstaða — Heitt eða kalt á íslenska fasteignamarkaðnum",
  description:
    "Regime indicator fyrir íslenska fasteignamarkaðinn: 23 cells af 33 fitted. Above-list rate timeline, heat map og back-projection per eign.",
  alternates: { canonical: "https://verdmat-is.vercel.app/markadur/markadsstada" },
  openGraph: {
    title: "Markaðsstaða — Verdmat",
    description:
      "Hvaða segmentir eru heitir eða kaldir á íslenska fasteignamarkaðnum. Uppfært mánaðarlega.",
    type: "website",
    locale: "is_IS",
  },
};

async function fetchMonthlyHeat() {
  // Reads the regime_per_cell_monthly view so the client gets raw, smoothed,
  // quarterly, display regime, and the regime_source label in one round-trip.
  // See migration 20260424_ats_lookup_by_quarter_and_regime_view.sql.
  const pageSize = 1000;
  let all = [];
  for (let from = 0; from < 10000; from += pageSize) {
    const to = from + pageSize - 1;
    const { data, error } = await supabase
      .from("regime_per_cell_monthly")
      .select(
        "canonical_code, region_tier, month, n_month, median_month, " +
          "above_list_rate, z_3v12, raw_regime, smoothed_regime, " +
          "quarterly_regime, quarterly_n_pairs, quarterly_period, " +
          "quarterly_data_quality, display_regime, regime_source",
      )
      .order("canonical_code", { ascending: true })
      .order("region_tier", { ascending: true })
      .order("month", { ascending: true })
      .range(from, to);
    if (error) {
      console.error("[markadsstada] regime view fetch failed", error);
      break;
    }
    if (!data || data.length === 0) break;
    all = all.concat(data);
    if (data.length < pageSize) break;
  }
  return all;
}

export default async function MarkadsstadaPage() {
  const monthlyRows = await fetchMonthlyHeat();

  return (
    <main className="vm-container" style={{ padding: "2.5rem 0 4rem" }}>
      <p style={{ marginBottom: "1rem" }}>
        <Link href="/markadur" style={{ fontSize: "0.9rem", color: "var(--vm-ink-muted)" }}>
          ← Markaður
        </Link>
      </p>

      <h1
        className="display"
        style={{
          fontSize: "clamp(2rem, 4vw, 2.75rem)",
          marginBottom: "0.35rem",
          lineHeight: 1.1,
        }}
      >
        Markaðsstaða
      </h1>
      <p
        style={{
          color: "var(--vm-ink-muted)",
          fontSize: "1rem",
          maxWidth: 720,
          marginBottom: "0.75rem",
        }}
      >
        Hvaða segmentir eru heitir eða kaldir — tímabundið drífari í takt við slider-ið.
      </p>
      <p
        style={{
          fontSize: "0.85rem",
          color: "var(--vm-ink-muted)",
          background: "rgba(212, 179, 70, 0.10)",
          border: "1px solid rgba(212, 179, 70, 0.35)",
          borderRadius: 6,
          padding: "0.55rem 0.85rem",
          maxWidth: 760,
          lineHeight: 1.5,
          marginBottom: "2rem",
        }}
      >
        Nýjustu áreiðanlegu gögn eru frá 2025-Q2 vegna tímabundinnar
        takmörkunar á auglýsingaflæði. Fyllri gögn frá 2025-Q3 og áfram koma
        þegar nýr scraper er kominn í gang (Sprint 3 forgangur).
      </p>

      <MarkadsstadaDashboard monthlyRows={monthlyRows} />
      <BackProjectionWidget />
    </main>
  );
}
