import { notFound } from "next/navigation";
import Image from "next/image";
import { supabase } from "@/lib/supabase";
import {
  formatKr,
  formatMillions,
  formatM2,
  formatSegment,
  formatDate,
  heatBucketLabel,
} from "@/lib/format";
import PredictionCard from "@/components/PredictionCard";
import AttributionWaterfall from "@/components/AttributionWaterfall";
import CompsGrid from "@/components/CompsGrid";
import SalesHistoryTable from "@/components/SalesHistoryTable";
import MarketContextCard from "@/components/MarketContextCard";
import PhotoGallery from "@/components/PhotoGallery";
import PropertyMap from "@/components/PropertyMapClient";

export const revalidate = 600;

export async function generateMetadata({ params }) {
  const { fastnum } = await params;
  const { data } = await supabase
    .from("properties")
    .select("heimilisfang, postnr, postheiti, canonical_code")
    .eq("fastnum", fastnum)
    .maybeSingle();
  if (!data) return { title: "Eign ekki fundin — verdmat.is" };
  return {
    title: `${data.heimilisfang}, ${data.postnr} ${data.postheiti} — verdmat.is`,
    description: `AI-verðmat fyrir ${data.heimilisfang} (${formatSegment(data.canonical_code)}) byggt á þinglýstum kaupsamningum.`,
  };
}

export default async function PropertyPage({ params }) {
  const { fastnum } = await params;
  const fnum = Number(fastnum);
  if (!Number.isFinite(fnum)) notFound();

  const [
    { data: property },
    { data: prediction },
    { data: attributions },
    { data: compsRaw },
    { data: salesHistory },
  ] = await Promise.all([
    supabase.from("properties").select("*").eq("fastnum", fnum).maybeSingle(),
    supabase.from("predictions").select("*").eq("fastnum", fnum).maybeSingle(),
    supabase
      .from("feature_attributions")
      .select("*")
      .eq("fastnum", fnum)
      .order("rank", { ascending: true }),
    supabase
      .from("comps_index")
      .select("rank, comp_fastnum, distance_score, last_sale_date, last_sale_price_real")
      .eq("fastnum", fnum)
      .order("rank", { ascending: true })
      .limit(6),
    supabase
      .from("sales_history")
      .select("*")
      .eq("fastnum", fnum)
      .order("thinglystdags", { ascending: false }),
  ]);

  if (!property) notFound();

  // Enrich comps with property details in one query
  let comps = [];
  if (compsRaw && compsRaw.length) {
    const ids = compsRaw.map((c) => c.comp_fastnum);
    const { data: compProps } = await supabase
      .from("properties")
      .select(
        "fastnum, heimilisfang, postnr, postheiti, canonical_code, einflm, byggar, first_photo_url"
      )
      .in("fastnum", ids);
    const byId = new Map((compProps || []).map((p) => [p.fastnum, p]));
    comps = compsRaw.map((c) => ({ ...c, prop: byId.get(c.comp_fastnum) }));
  }

  // Market context (match heat_bucket = 'neutral' for baseline display; future: pick dynamically)
  let marketRows = [];
  if (property.canonical_code && property.region_tier) {
    const { data: mkt } = await supabase
      .from("ats_lookup")
      .select("*")
      .eq("canonical_code", property.canonical_code)
      .eq("region_tier", property.region_tier);
    marketRows = mkt || [];
  }

  const photos = parsePhotos(property.photo_urls_json, property.first_photo_url);

  return (
    <main className="vm-container" style={{ padding: "2rem 0 4rem" }}>
      {/* Row 1 — Hero */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "3fr 2fr",
          gap: "2rem",
          marginBottom: "2rem",
        }}
      >
        <PhotoGallery photos={photos} title={property.heimilisfang} />
        <div>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--vm-accent)",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: "0.5rem",
            }}
          >
            Fastanúmer {property.fastnum}
          </div>
          <h1
            className="display"
            style={{ fontSize: "2.25rem", marginBottom: "0.5rem" }}
          >
            {property.heimilisfang}
          </h1>
          <div
            style={{
              color: "var(--vm-ink-muted)",
              fontSize: "1.05rem",
              marginBottom: "1.25rem",
            }}
          >
            {property.postnr} {property.postheiti}
            {property.sveitarfelag ? ` · ${property.sveitarfelag}` : ""}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap: "0.75rem 1.25rem",
              padding: "1rem 1.25rem",
              background: "var(--vm-surface)",
              borderRadius: 10,
              border: "1px solid var(--vm-border)",
              marginBottom: "1.25rem",
            }}
          >
            <Stat label="Gerð" value={formatSegment(property.canonical_code)} />
            <Stat label="Stærð" value={formatM2(property.einflm)} />
            <Stat label="Byggt" value={property.byggar ?? "—"} />
            <Stat
              label="Herbergi"
              value={property.fjherb != null ? property.fjherb : "—"}
            />
            <Stat
              label="Fasteignamat"
              value={
                property.fasteignamat
                  ? formatMillions(property.fasteignamat * 1000, 1)
                  : "—"
              }
            />
            <Stat label="Matsvæði" value={property.matsvaedi_nafn ?? "—"} />
          </div>
          {property.augl_id_latest && property.list_price_latest ? (
            <div
              style={{
                fontSize: "0.9rem",
                color: "var(--vm-ink-muted)",
              }}
            >
              Nýleg auglýsing á ásettu verði{" "}
              <strong
                className="tabular"
                style={{ color: "var(--vm-ink)" }}
              >
                {formatMillions(property.list_price_latest * 1000)}
              </strong>
              {property.scraped_at_latest
                ? ` (${formatDate(property.scraped_at_latest)})`
                : ""}
            </div>
          ) : null}
        </div>
      </section>

      {/* Row 2 — Non-residential notice (suppresses prediction/SHAP/comps) */}
      {!property.is_residential && (
        <section
          className="vm-card vm-card-elevated"
          style={{
            marginBottom: "2rem",
            borderTop: "3px solid var(--vm-neutral)",
            padding: "1.75rem 2rem",
          }}
        >
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--vm-neutral)",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: "0.6rem",
            }}
          >
            Ekki í boði
          </div>
          <h2
            className="display"
            style={{ fontSize: "1.35rem", marginBottom: "0.5rem" }}
          >
            Verðmat er ekki í boði fyrir þessa eign
          </h2>
          <p style={{ color: "var(--vm-ink-muted)", lineHeight: 1.6 }}>
            Þessi eign er flokkuð sem{" "}
            <strong style={{ color: "var(--vm-ink)" }}>
              {formatSegment(property.canonical_code)}
            </strong>
            . verdmat.is sérhæfir sig í íbúðarhúsnæði (íbúðir, einbýli, raðhús
            o.s.frv.). Fyrir atvinnuhúsnæði eða ótilgreindar eignir er
            verðmatsmódelið ekki kvarðað.
          </p>
        </section>
      )}

      {/* Row 2 — Prediction card (residential only) */}
      {property.is_residential && prediction && (
        <PredictionCard
          prediction={prediction}
          fasteignamat={property.fasteignamat}
        />
      )}

      {/* Row 3 — SHAP waterfall (residential only) */}
      {property.is_residential && attributions && attributions.length > 0 && (
        <section
          className="vm-card vm-card-elevated"
          style={{ marginBottom: "2rem" }}
        >
          <h2
            className="display"
            style={{ fontSize: "1.5rem", marginBottom: "0.35rem" }}
          >
            Hvaða þættir knýja þetta mat?
          </h2>
          <p
            style={{
              color: "var(--vm-ink-muted)",
              marginBottom: "1.5rem",
              fontSize: "0.92rem",
            }}
          >
            Top-10 þættir raðaðir eftir áhrifum á verðið, mældir í krónum.
          </p>
          <AttributionWaterfall
            attributions={attributions}
            predMean={prediction?.real_pred_mean}
          />
        </section>
      )}

      {/* Row 4 — Map */}
      {property.lat && property.lng && (
        <section style={{ marginBottom: "2rem" }}>
          <h2
            className="display"
            style={{ fontSize: "1.5rem", marginBottom: "1rem" }}
          >
            Staðsetning
          </h2>
          <PropertyMap
            lat={property.lat}
            lng={property.lng}
            label={property.heimilisfang}
          />
        </section>
      )}

      {/* Row 5 — Comps (residential only) */}
      {property.is_residential && comps.length > 0 && (
        <section style={{ marginBottom: "2rem" }}>
          <h2
            className="display"
            style={{ fontSize: "1.5rem", marginBottom: "1rem" }}
          >
            Sambærilegar eignir í hverfinu
          </h2>
          <CompsGrid comps={comps} />
        </section>
      )}

      {/* Row 6 — Sales history */}
      {salesHistory && salesHistory.length > 0 && (
        <section style={{ marginBottom: "2rem" }}>
          <h2
            className="display"
            style={{ fontSize: "1.5rem", marginBottom: "1rem" }}
          >
            Sölusaga
          </h2>
          <SalesHistoryTable rows={salesHistory} />
        </section>
      )}

      {/* Row 7 — Market context (residential only) */}
      {property.is_residential && marketRows.length > 0 && (
        <section style={{ marginBottom: "2rem" }}>
          <h2
            className="display"
            style={{ fontSize: "1.5rem", marginBottom: "1rem" }}
          >
            Markaðsstaða
          </h2>
          <MarketContextCard
            rows={marketRows}
            segment={property.canonical_code}
            region={property.region_tier}
          />
        </section>
      )}
    </main>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div
        style={{
          fontSize: "0.72rem",
          color: "var(--vm-ink-faint)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: "0.2rem",
        }}
      >
        {label}
      </div>
      <div style={{ fontWeight: 500 }} className="tabular">
        {value}
      </div>
    </div>
  );
}

function parsePhotos(json, fallback) {
  if (!json) return fallback ? [fallback] : [];
  try {
    const arr = typeof json === "string" ? JSON.parse(json) : json;
    if (Array.isArray(arr)) return arr;
  } catch {
    // ignore
  }
  return fallback ? [fallback] : [];
}
