import { supabase } from "@/lib/supabase";
import RepeatSaleChart from "@/components/RepeatSaleChart";
import MarketHeatGrid from "@/components/MarketHeatGrid";

export const revalidate = 600;

export const metadata = {
  title: "Markaðsyfirlit — verdmat.is",
  description:
    "Repeat-sale vísitala, markaðshiti og afar áhrifamikil 2008-hrun-dýfa raunverðsins.",
};

async function fetchAllRepeatSaleIndex() {
  // PostgREST enforces max-rows=1000 on Supabase free tier even with .range().
  // repeat_sale_index has ~2,673 rows — paginate manually.
  const pageSize = 1000;
  let all = [];
  for (let from = 0; from < 10000; from += pageSize) {
    const to = from + pageSize - 1;
    const { data, error } = await supabase
      .from("repeat_sale_index")
      .select("*")
      .order("year", { ascending: true })
      .order("quarter", { ascending: true })
      .range(from, to);
    if (error || !data || data.length === 0) break;
    all = all.concat(data);
    if (data.length < pageSize) break;
  }
  return all;
}

export default async function MarketPage() {
  const [index, { data: atsRows }] = await Promise.all([
    fetchAllRepeatSaleIndex(),
    supabase.from("ats_lookup").select("*"),
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
        <RepeatSaleChart series={index} />
      </section>
    </main>
  );
}
