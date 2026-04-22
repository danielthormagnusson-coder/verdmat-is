import Link from "next/link";
import { supabase } from "@/lib/supabase";
import VisitalaGrid from "@/components/VisitalaGrid";
import VisitalaFindings from "@/components/VisitalaFindings";

export const revalidate = 600;

export const metadata = {
  title: "Raunverðs vísitala — Fasteignaverð á Íslandi 2006–2026",
  description:
    "Paired-resale vísitala fyrir íslenska fasteignamarkaðinn eftir segmenti og svæði. Raunverð vs nominal 2006Q2–nú.",
  openGraph: {
    title: "Raunverðs vísitala — Verdmat",
    description:
      "Paired-resale vísitala eftir segmenti og svæði, 2006Q2 = 100.",
    type: "website",
    locale: "is_IS",
  },
};

// Columns the grid actually reads — matches VisitalaGrid + SubChart + tooltip.
const COLS =
  "canonical_code,region_tier,year,quarter,period," +
  "index_value_real,index_value_nominal," +
  "std_error_real,std_error_nominal," +
  "n_pairs_in_period,data_quality,insufficient_sample";

async function fetchRepeatSaleAll() {
  const pageSize = 1000;
  let all = [];
  for (let from = 0; from < 10000; from += pageSize) {
    const to = from + pageSize - 1;
    const { data, error } = await supabase
      .from("repeat_sale_index")
      .select(COLS)
      .order("canonical_code", { ascending: true })
      .order("region_tier", { ascending: true })
      .order("year", { ascending: true })
      .order("quarter", { ascending: true })
      .range(from, to);
    if (error || !data || data.length === 0) break;
    all = all.concat(data);
    if (data.length < pageSize) break;
  }
  return all;
}

export default async function VisitalaPage() {
  const rows = await fetchRepeatSaleAll();

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
        Raunverðs vísitala
      </h1>
      <p
        style={{
          color: "var(--vm-ink-muted)",
          fontSize: "1rem",
          maxWidth: 720,
          marginBottom: "2rem",
        }}
      >
        Paired-resale vísitala eftir segmenti og svæði, 2006Q2 = 100.
      </p>

      <VisitalaGrid allRows={rows} />

      <VisitalaFindings />
    </main>
  );
}
