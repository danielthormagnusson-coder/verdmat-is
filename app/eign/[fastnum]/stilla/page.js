import { notFound, redirect } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { formatSegment, formatMillions, formatM2 } from "@/lib/format";
import QuestionnaireClient from "./QuestionnaireClient";

export const revalidate = 600;

export async function generateMetadata({ params }) {
  const { fastnum } = await params;
  const { data } = await supabase
    .from("properties")
    .select("heimilisfang")
    .eq("fastnum", fastnum)
    .maybeSingle();
  if (!data) return { title: "Stilla verðmat — verdmat.is" };
  return {
    title: `Stilla verðmat fyrir ${data.heimilisfang} — verdmat.is`,
  };
}

export default async function StillaPage({ params }) {
  const { fastnum } = await params;
  const fnum = Number(fastnum);
  if (!Number.isFinite(fnum)) notFound();

  const { data: property } = await supabase
    .from("properties")
    .select(
      "fastnum, heimilisfang, postnr, postheiti, canonical_code, einflm, byggar, is_residential"
    )
    .eq("fastnum", fnum)
    .maybeSingle();

  if (!property) notFound();

  // Non-residential or summerhouse: redirect back with notice
  if (!property.is_residential) {
    redirect(`/eign/${fnum}?notice=no_adjust`);
  }
  if (property.canonical_code === "SUMMERHOUSE") {
    redirect(`/eign/${fnum}?notice=no_adjust`);
  }

  const { data: prediction } = await supabase
    .from("predictions")
    .select("real_pred_mean, real_pred_lo80, real_pred_hi80")
    .eq("fastnum", fnum)
    .maybeSingle();

  return (
    <main className="vm-container" style={{ padding: "2.5rem 0 4rem", maxWidth: 780 }}>
      <section style={{ marginBottom: "2rem" }}>
        <a
          href={`/eign/${fnum}`}
          style={{ fontSize: "0.88rem", color: "var(--vm-ink-muted)" }}
        >
          ← Til baka á eignasíðu
        </a>
        <h1
          className="display"
          style={{
            fontSize: "2.25rem",
            marginTop: "0.75rem",
            marginBottom: "0.5rem",
          }}
        >
          Stilla verðmat
        </h1>
        <div
          style={{
            color: "var(--vm-ink-muted)",
            fontSize: "1.05rem",
            marginBottom: "1.5rem",
          }}
        >
          {property.heimilisfang}, {property.postnr} {property.postheiti}
          {" · "}
          {formatSegment(property.canonical_code)}
          {property.einflm ? ` · ${formatM2(property.einflm)}` : ""}
          {property.byggar ? ` · byggt ${Math.round(property.byggar)}` : ""}
        </div>
        {prediction && (
          <div
            className="vm-card"
            style={{
              background: "var(--vm-surface)",
              padding: "1rem 1.25rem",
              fontSize: "0.95rem",
            }}
          >
            Grunnverðmat í dag:{" "}
            <strong
              className="tabular"
              style={{ color: "var(--vm-ink)", fontFamily: "var(--font-display)" }}
            >
              {formatMillions(prediction.real_pred_mean)}
            </strong>
            {" · "}
            <span style={{ color: "var(--vm-ink-muted)" }}>
              80% bil {formatMillions(prediction.real_pred_lo80)} –{" "}
              {formatMillions(prediction.real_pred_hi80)}
            </span>
          </div>
        )}
      </section>

      <QuestionnaireClient fastnum={fnum} canonical={property.canonical_code} />
    </main>
  );
}
