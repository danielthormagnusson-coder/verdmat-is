import { supabase } from "@/lib/supabase";
import RepeatSaleChart from "@/components/RepeatSaleChart";
import MarketHeatGrid from "@/components/MarketHeatGrid";

export const revalidate = 600;

export const metadata = {
  title: "Markaðsyfirlit — verdmat.is",
  description:
    "Repeat-sale vísitala, markaðshiti og afar áhrifamikil 2008-hrun-dýfa raunverðsins.",
};

export default async function MarketPage() {
  const [{ data: index }, { data: atsRows }] = await Promise.all([
    // Supabase defaults to a 1000-row cap for anon/authenticated reads;
    // repeat_sale_index has ~2,673 rows (segments × regions × quarters), so
    // bypass the default via .range(0, 9999).
    supabase
      .from("repeat_sale_index")
      .select("*")
      .order("year", { ascending: true })
      .order("quarter", { ascending: true })
      .range(0, 9999),
    supabase.from("ats_lookup").select("*").range(0, 999),
  ]);

  return (
    <main className="vm-container" style={{ padding: "3rem 0 4rem" }}>
      <section style={{ marginBottom: "3rem" }}>
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--vm-accent)",
            fontWeight: 600,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            marginBottom: "0.75rem",
          }}
        >
          MARKAÐURINN Í DAG
        </p>
        <h1
          className="display"
          style={{
            fontSize: "clamp(2.25rem, 4.5vw, 3.25rem)",
            marginBottom: "0.5rem",
          }}
        >
          Heitir og kaldir reitir
        </h1>
        <p
          style={{
            fontSize: "1.05rem",
            color: "var(--vm-ink-muted)",
            maxWidth: 720,
            lineHeight: 1.55,
          }}
        >
          Hlutfall sala sem fara yfir ásettu verði, brotið niður á eignaflokk
          og landshluta. Mælir markaðsþrýsting á hverjum reit.
        </p>
      </section>

      <section style={{ marginBottom: "3.5rem" }}>
        <MarketHeatGrid rows={atsRows || []} />
      </section>

      <section style={{ marginBottom: "3rem" }}>
        <h2
          className="display"
          style={{ fontSize: "1.75rem", marginBottom: "0.4rem" }}
        >
          Repeat-sale vísitala
        </h2>
        <p
          style={{
            color: "var(--vm-ink-muted)",
            marginBottom: "1.5rem",
            fontSize: "0.95rem",
            maxWidth: 700,
          }}
        >
          Verðþróun miðað við 2006Q2 = 100, mældur sem paraðar endursölur sömu
          eignar. Raunlína (CPI-deflated) sýnir raunverðsdýfu 2008–2011; nominal
          lína sýnir hvar peningaverð hefur lent.
        </p>
        <RepeatSaleChart series={index || []} />
      </section>
    </main>
  );
}
