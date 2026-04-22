import Link from "next/link";
import { supabase } from "@/lib/supabase";
import {
  ConditionChart,
  RenovationChart,
  UnregisteredBarChart,
  SerlodSmallMultiples,
  FramingStackedArea,
} from "@/components/IbudirCharts";

export const revalidate = 600;

export const metadata = {
  title: "Íbúðaástand á Íslandi — AI-greining á 37.544 sölulýsingum",
  description:
    "Ástandsvísitala, endurnýjunartíðni, óskráð rými, sérlóðir og agent-framing yfir 20 ára tímabil. Gögn úr AI-greiningu á lýsingum úr íslenskum fasteignaauglýsingum.",
  openGraph: {
    title: "Íbúðaástand á Íslandi — Verdmat",
    description:
      "Hvernig hafa íbúðirnar sjálfar breyst síðustu 20 ár — ástand, endurnýjun, óskráð rými, sérlóðir og orðræðu-framing.",
    type: "website",
    locale: "is_IS",
  },
};

async function fetchLlmAggregates() {
  const pageSize = 1000;
  let all = [];
  for (let from = 0; from < 10000; from += pageSize) {
    const to = from + pageSize - 1;
    const { data, error } = await supabase
      .from("llm_aggregates_quarterly")
      .select(
        "year, quarter, period, canonical_code, region_tier, " +
          "mean_interior_condition_score, n_listings_condition, " +
          "pct_recently_renovated, n_listings_renovation, " +
          "pct_has_unregistered_space, n_listings_unregistered, " +
          "pct_apt_with_serlod, n_listings_serlod, " +
          "pct_framing_terse, pct_framing_standard, " +
          "pct_framing_elaborate, pct_framing_promotional, " +
          "n_listings_total",
      )
      .order("period", { ascending: true })
      .order("canonical_code", { ascending: true })
      .order("region_tier", { ascending: true })
      .range(from, to);
    if (error || !data || data.length === 0) break;
    all = all.concat(data);
    if (data.length < pageSize) break;
  }
  return all;
}

function Section({ eyebrow, title, editorialHook, narrativeArc, children, callout }) {
  return (
    <section style={{ marginBottom: "3rem" }}>
      <p
        style={{
          fontSize: "0.72rem",
          color: "var(--vm-accent)",
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          marginBottom: "0.3rem",
        }}
      >
        {eyebrow}
      </p>
      <h2
        className="display"
        style={{ fontSize: "1.55rem", marginBottom: "0.4rem", lineHeight: 1.2 }}
      >
        {title}
      </h2>
      <p
        style={{
          fontSize: "0.95rem",
          color: "var(--vm-ink-muted)",
          maxWidth: 720,
          marginBottom: "0.6rem",
          lineHeight: 1.55,
        }}
      >
        <strong style={{ color: "var(--vm-ink)", fontWeight: 500 }}>
          {editorialHook}
        </strong>{" "}
        {narrativeArc}
      </p>
      {children}
      {callout ? (
        <p
          style={{
            fontSize: "0.8rem",
            color: "var(--vm-ink-faint)",
            marginTop: "0.5rem",
            fontStyle: "italic",
          }}
        >
          {callout}
        </p>
      ) : null}
    </section>
  );
}

export default async function IbudirPage() {
  const rows = await fetchLlmAggregates();
  const pooled = rows.filter((r) => r.region_tier === "POOLED");
  const perRegion = rows.filter((r) => r.region_tier !== "POOLED");

  return (
    <main className="vm-container" style={{ padding: "2.5rem 0 4rem" }}>
      <p style={{ marginBottom: "1rem" }}>
        <Link
          href="/markadur"
          style={{ fontSize: "0.9rem", color: "var(--vm-ink-muted)" }}
        >
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
        Íbúðaástand
      </h1>
      <p
        style={{
          color: "var(--vm-ink-muted)",
          fontSize: "1rem",
          maxWidth: 720,
          marginBottom: "0.25rem",
        }}
      >
        Hvernig hafa íbúðirnar sjálfar breyst síðustu 20 ár?
      </p>
      <p
        style={{
          fontSize: "0.85rem",
          color: "var(--vm-ink-faint)",
          maxWidth: 720,
          marginBottom: "2.5rem",
        }}
      >
        Byggt á AI-greiningu á 37.544 sölulýsingum úr íslenskum
        fasteignaauglýsingum 2006–2025. Metric 5 (orðatíðni) er áformuð í
        v1.1 uppfærslu.
      </p>

      <Section
        eyebrow="1. Ástandsvísitala"
        title="Innra ástand íbúða yfir tíma"
        editorialHook="Hefur ástand íbúða á íslenska markaðnum farið upp eða niður síðustu 20 ár?"
        narrativeArc="Meðaltal innra-ástandsstig (-2 … 3 skali úr LLM-greiningu) per ársfjórðungi fyrir þrjú meginsegment. Hækkandi kúrfa vísar á sellera sem taka í gegn fyrir sölu."
        callout="Key callout (TBD með rauntölum): segment × tímabil með mestri hækkun eða lækkun — fær final prose í v1.1."
      >
        <ConditionChart pooled={pooled} />
      </Section>

      <Section
        eyebrow="2. Endurnýjunartíðni"
        title="Hlutfall eigna með nýlegar endurbætur"
        editorialHook="Eru nýlegar endurbætur algengari á heitum markaði en köldum?"
        narrativeArc="Hlutfall auglýsinga þar sem a.m.k. einn hluti eignar (eldhús, bað, gólfefni, málning) var endurnýjaður á síðustu 5 árum, per segment."
        callout="Key callout (TBD): benda á peak-ár + samhengi við regime cycle."
      >
        <RenovationChart pooled={pooled} />
      </Section>

      <Section
        eyebrow="3. Óskráð rými"
        title="Eignir með óskráð pláss, eftir svæði"
        editorialHook="Hvar á landinu er algengast að íbúðir hafi óskráð rými?"
        narrativeArc="Weighted meðalhlutfall auglýsinga með has_unregistered_space = true, per svæði og segmenti. Höfðar til SFH_DETACHED Country sem útreikningur Áfanga 3 benti á sem hotspot."
        callout="Key callout (TBD): staðfesta SFH_DETACHED Country hlutfall með raun-tölu þegar v1.1 editorial drög eru skrifuð."
      >
        <UnregisteredBarChart perRegion={perRegion} />
      </Section>

      <Section
        eyebrow="4. Sérlóð í APT"
        title="Íbúðir með sérlóð, per svæði"
        editorialHook="Hvar finnast sérlóðir með íbúðum?"
        narrativeArc="Hlutfall APT_FLOOR og APT_STANDARD auglýsinga með lot_is_serlod flag. Íslenskt sérkenni — fjarverandi í evrópskum markaði."
        callout="Key callout (TBD): identify svæði/segment combo sem víkur mest frá meðaltali."
      >
        <SerlodSmallMultiples perRegion={perRegion} />
      </Section>

      <Section
        eyebrow="6. Agent-framing"
        title="Hvernig seljendur pakka auglýsingum"
        editorialHook={"Hefur söluhrifið orðalag („einstakt tækifæri“) orðið algengara á heitum markaði?"}
        narrativeArc="Dreifing fjögurra framing-flokka (hófstillt / stöðluð / ítarleg / söluhrifin) úr LLM-greiningu, pooled yfir svæði fyrir APT_STANDARD. Stacked area sýnir hlutfallslega tilfærslu yfir tíma."
        callout="Key callout (TBD): spike í söluhrifið/ítarleg framing í early-2022 bidding war + niðurhvarf í late-2023."
      >
        <FramingStackedArea pooled={pooled} />
      </Section>

      <footer
        style={{
          marginTop: "3rem",
          padding: "1rem 0",
          borderTop: "1px solid var(--vm-border)",
          fontSize: "0.8rem",
          color: "var(--vm-ink-faint)",
        }}
      >
        <Link href="/um#adferdafraedi" style={{ color: "var(--vm-primary)" }}>
          Aðferðafræði →
        </Link>
      </footer>
    </main>
  );
}
