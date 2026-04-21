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
import Link from "next/link";

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

export default async function PropertyPage({ params, searchParams }) {
  const { fastnum } = await params;
  const sp = (await searchParams) || {};
  const showDebug = sp.mode === "debug";
  const fnum = Number(fastnum);
  if (!Number.isFinite(fnum)) notFound();

  const queries = [
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
  ];
  if (showDebug) {
    queries.push(
      supabase
        .from("predictions_iter3v2")
        .select("*")
        .eq("fastnum", fnum)
        .maybeSingle()
    );
  }

  const results = await Promise.all(queries);
  const { data: property } = results[0];
  const { data: prediction } = results[1];
  const { data: attributions } = results[2];
  const { data: compsRaw } = results[3];
  const { data: salesHistory } = results[4];
  const iter3Prediction = showDebug ? results[5]?.data : null;

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
              label="HMS-fasteignamat"
              value={
                property.fasteignamat
                  ? formatMillions(property.fasteignamat * 1000, 1)
                  : "—"
              }
            />
            <Stat label="Matsvæði" value={property.matsvaedi_nafn ?? "—"} />
          </div>
          {property.fasteignamat ? (
            <div
              style={{
                fontSize: "0.8rem",
                color: "var(--vm-ink-faint)",
                marginBottom: "0.9rem",
                lineHeight: 1.5,
                fontStyle: "italic",
              }}
            >
              Opinber HMS-eignamat er viðmiðun. verdmat.is spá er reiknuð
              sjálfstætt, án fasteignamats-inntaks.
            </div>
          ) : null}
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
              {property.effective_date_latest
                ? ` (${formatDate(property.effective_date_latest)})`
                : property.scraped_at_latest
                ? ` (skráð ${formatDate(property.scraped_at_latest)})`
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

      {/* CTA — Stilla verðmat (residential, non-summer only) */}
      {property.is_residential && property.canonical_code !== "SUMMERHOUSE" && prediction && (
        <section
          className="vm-card vm-card-elevated"
          style={{
            marginBottom: "2rem",
            background: "rgba(229, 183, 158, 0.22)",
            borderColor: "var(--vm-accent-soft)",
            padding: "1.5rem 1.75rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1.25rem",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h3 className="display" style={{ fontSize: "1.25rem", marginBottom: "0.35rem" }}>
              Viltu nákvæmara verðmat?
            </h3>
            <p style={{ color: "var(--vm-ink-muted)", fontSize: "0.92rem", lineHeight: 1.55, maxWidth: 540 }}>
              Svaraðu nokkrum spurningum um ástand, útsýni og útiþætti — ég reikna
              persónulegt verðmat byggt á þínum upplýsingum.
            </p>
          </div>
          <Link href={`/eign/${fnum}/stilla`} className="vm-btn" style={{ textDecoration: "none" }}>
            Stilla verðmat
          </Link>
        </section>
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

      {/* Row 8 — Debug mode: model comparison */}
      {showDebug && property.is_residential && prediction && (
        <section
          className="vm-card"
          style={{
            marginTop: "3rem",
            background: "var(--vm-surface)",
            border: "1px dashed var(--vm-border-strong)",
            padding: "1.5rem 1.75rem",
          }}
        >
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--vm-ink-faint)",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: "0.5rem",
            }}
          >
            DEBUG MODE
          </div>
          <h2
            className="display"
            style={{ fontSize: "1.3rem", marginBottom: "1rem" }}
          >
            Samanburður módela
          </h2>
          <table
            style={{
              width: "100%",
              fontSize: "0.92rem",
              borderCollapse: "collapse",
            }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid var(--vm-border)" }}>
                <th style={{ textAlign: "left", padding: "0.5rem 0", color: "var(--vm-ink-muted)", fontWeight: 600 }}>Model</th>
                <th style={{ textAlign: "right", padding: "0.5rem 0", color: "var(--vm-ink-muted)", fontWeight: 600 }}>Mean spá</th>
                <th style={{ textAlign: "right", padding: "0.5rem 0", color: "var(--vm-ink-muted)", fontWeight: 600 }}>80% PI</th>
                <th style={{ textAlign: "left", padding: "0.5rem 0", color: "var(--vm-ink-muted)", fontWeight: 600, paddingLeft: "1rem" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid var(--vm-border)" }}>
                <td style={{ padding: "0.6rem 0", fontWeight: 500 }}>iter4 (production)</td>
                <td className="tabular" style={{ textAlign: "right", padding: "0.6rem 0" }}>
                  {formatMillions(prediction.real_pred_mean)}
                </td>
                <td className="tabular" style={{ textAlign: "right", padding: "0.6rem 0" }}>
                  {formatMillions(prediction.real_pred_lo80)} – {formatMillions(prediction.real_pred_hi80)}
                </td>
                <td style={{ padding: "0.6rem 0", paddingLeft: "1rem", color: "var(--vm-success)" }}>
                  standalone · no fastmat input
                </td>
              </tr>
              {iter3Prediction ? (
                <tr style={{ borderBottom: "1px solid var(--vm-border)" }}>
                  <td style={{ padding: "0.6rem 0" }}>iter3v2 (archived)</td>
                  <td className="tabular" style={{ textAlign: "right", padding: "0.6rem 0" }}>
                    {formatMillions(iter3Prediction.real_pred_mean)}
                  </td>
                  <td className="tabular" style={{ textAlign: "right", padding: "0.6rem 0" }}>
                    {formatMillions(iter3Prediction.real_pred_lo80)} – {formatMillions(iter3Prediction.real_pred_hi80)}
                  </td>
                  <td style={{ padding: "0.6rem 0", paddingLeft: "1rem", color: "var(--vm-ink-muted)" }}>
                    fastmat-dependent
                  </td>
                </tr>
              ) : null}
              {property.fasteignamat ? (
                <tr>
                  <td style={{ padding: "0.6rem 0", color: "var(--vm-ink-muted)" }}>HMS fasteignamat</td>
                  <td className="tabular" style={{ textAlign: "right", padding: "0.6rem 0", color: "var(--vm-ink-muted)" }}>
                    {formatMillions(property.fasteignamat * 1000)}
                  </td>
                  <td></td>
                  <td style={{ padding: "0.6rem 0", paddingLeft: "1rem", color: "var(--vm-ink-faint)", fontStyle: "italic" }}>
                    reference only
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
          {iter3Prediction ? (
            <p style={{ marginTop: "1rem", color: "var(--vm-ink-muted)", fontSize: "0.88rem", lineHeight: 1.55 }}>
              Delta iter4 vs iter3v2:{" "}
              <strong className="tabular" style={{ color: "var(--vm-ink)" }}>
                {(
                  (100 * (prediction.real_pred_mean - iter3Prediction.real_pred_mean)) /
                  iter3Prediction.real_pred_mean
                ).toFixed(1)}
                %
              </strong>
              . iter4 er óháður fasteignamati HMS — árleg HMS-uppfærsla (júní) breytir spánni ekki.
            </p>
          ) : null}
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
