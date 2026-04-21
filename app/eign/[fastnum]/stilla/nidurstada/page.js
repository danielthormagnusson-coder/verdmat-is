import { notFound } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import effects from "@/data/manual_q_effects.json";
import {
  formatMillions,
  formatSegment,
  formatM2,
  formatPercent,
} from "@/lib/format";
import ShareButton from "./ShareButton";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export const metadata = {
  title: "Persónulegt verðmat — verdmat.is",
};

function parseAnswers(a) {
  if (!a) return {};
  const out = {};
  for (const pair of a.split(",")) {
    const [k, v] = pair.split(":");
    if (k && v) out[k.trim()] = v.trim();
  }
  return out;
}

function computeAdjustment(answers) {
  const qMap = effects.questions || {};
  let logAdjustment = 0;
  const breakdown = [];
  for (const [question, value] of Object.entries(answers)) {
    const q = qMap[question];
    if (!q) continue;
    const e = q.effects?.[value];
    if (typeof e !== "number") continue;
    logAdjustment += Math.log(1 + e);
    breakdown.push({
      question,
      label: q.label,
      value,
      effect: e,
    });
  }
  return { logAdjustment, breakdown, multiplier: Math.exp(logAdjustment) };
}

export default async function NidurstadaPage({ params, searchParams }) {
  const { fastnum } = await params;
  const sp = (await searchParams) || {};
  const answers = parseAnswers(sp.a);
  const fnum = Number(fastnum);
  if (!Number.isFinite(fnum)) notFound();

  const [{ data: property }, { data: prediction }] = await Promise.all([
    supabase
      .from("properties")
      .select(
        "fastnum, heimilisfang, postnr, postheiti, canonical_code, einflm, byggar, fasteignamat"
      )
      .eq("fastnum", fnum)
      .maybeSingle(),
    supabase
      .from("predictions")
      .select(
        "real_pred_mean, real_pred_median, real_pred_lo80, real_pred_hi80, real_pred_lo95, real_pred_hi95, model_version, calibration_version"
      )
      .eq("fastnum", fnum)
      .maybeSingle(),
  ]);

  if (!property || !prediction) notFound();

  const { breakdown, multiplier } = computeAdjustment(answers);
  const baseline = {
    mean: Number(prediction.real_pred_mean),
    lo80: Number(prediction.real_pred_lo80),
    hi80: Number(prediction.real_pred_hi80),
    lo95: Number(prediction.real_pred_lo95),
    hi95: Number(prediction.real_pred_hi95),
  };
  const adjusted = {
    mean: Math.round(baseline.mean * multiplier),
    lo80: Math.round(baseline.lo80 * multiplier),
    hi80: Math.round(baseline.hi80 * multiplier),
    lo95: Math.round(baseline.lo95 * multiplier),
    hi95: Math.round(baseline.hi95 * multiplier),
  };
  const deltaIsk = adjusted.mean - baseline.mean;
  const deltaPct = (deltaIsk / baseline.mean) * 100;
  const withImpact = breakdown.map((b) => ({
    ...b,
    impact_isk: Math.round(baseline.mean * b.effect),
  }));
  withImpact.sort(
    (a, b) => Math.abs(b.impact_isk) - Math.abs(a.impact_isk)
  );

  return (
    <main className="vm-container" style={{ padding: "2.5rem 0 4rem", maxWidth: 820 }}>
      <section style={{ marginBottom: "1.5rem" }}>
        <a
          href={`/eign/${fnum}`}
          style={{ fontSize: "0.88rem", color: "var(--vm-ink-muted)" }}
        >
          ← Eignasíða
        </a>
        <h1
          className="display"
          style={{ fontSize: "2.25rem", marginTop: "0.6rem", marginBottom: "0.25rem" }}
        >
          Persónulegt verðmat
        </h1>
        <div
          style={{
            color: "var(--vm-ink-muted)",
            fontSize: "1.05rem",
          }}
        >
          {property.heimilisfang}, {property.postnr} {property.postheiti}
          {" · "}
          {formatSegment(property.canonical_code)}
          {property.einflm ? ` · ${formatM2(property.einflm)}` : ""}
        </div>
      </section>

      <section
        className="vm-card vm-card-elevated"
        style={{
          marginBottom: "2rem",
          borderTop: "3px solid var(--vm-accent)",
          padding: "2rem 2.25rem",
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
          <div>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--vm-ink-muted)",
                fontWeight: 600,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: "0.35rem",
              }}
            >
              Grunnverðmat
            </div>
            <div
              className="display tabular"
              style={{
                fontSize: "1.9rem",
                color: "var(--vm-ink-muted)",
                lineHeight: 1.1,
              }}
            >
              {formatMillions(baseline.mean)}
            </div>
          </div>
          <div>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--vm-accent)",
                fontWeight: 600,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: "0.35rem",
              }}
            >
              Persónulegt
            </div>
            <div
              className="display tabular"
              style={{
                fontSize: "clamp(2.2rem, 4.2vw, 3rem)",
                lineHeight: 1.05,
              }}
            >
              {formatMillions(adjusted.mean)}
            </div>
          </div>
        </div>

        <div
          style={{
            marginTop: "1.5rem",
            padding: "0.9rem 1.1rem",
            background: "var(--vm-surface)",
            borderRadius: 8,
            display: "flex",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "0.75rem",
          }}
        >
          <div style={{ fontSize: "0.95rem", color: "var(--vm-ink-muted)" }}>
            Breyting miðað við grunn:{" "}
            <strong
              style={{
                color:
                  deltaPct > 0
                    ? "var(--vm-success)"
                    : deltaPct < 0
                    ? "var(--vm-danger)"
                    : "var(--vm-ink)",
              }}
              className="tabular"
            >
              {deltaPct > 0 ? "+" : ""}
              {formatMillions(deltaIsk)}
              {" "}({deltaPct > 0 ? "+" : ""}{deltaPct.toFixed(1)}%)
            </strong>
          </div>
          <div
            style={{ fontSize: "0.85rem", color: "var(--vm-ink-faint)" }}
            className="tabular"
          >
            80% bil: {formatMillions(adjusted.lo80)} – {formatMillions(adjusted.hi80)}
          </div>
        </div>
      </section>

      {withImpact.length > 0 && (
        <section
          className="vm-card vm-card-elevated"
          style={{ marginBottom: "2rem" }}
        >
          <h2
            className="display"
            style={{ fontSize: "1.35rem", marginBottom: "0.5rem" }}
          >
            Hvernig svörin þín breyta matinu
          </h2>
          <p
            style={{
              fontSize: "0.92rem",
              color: "var(--vm-ink-muted)",
              marginBottom: "1.25rem",
            }}
          >
            Top þættir raðaðir eftir áhrifum í krónum.
          </p>
          <AdjustmentWaterfall rows={withImpact} baselineMean={baseline.mean} />
        </section>
      )}

      <section
        style={{
          display: "flex",
          gap: "0.75rem",
          flexWrap: "wrap",
          marginBottom: "2rem",
        }}
      >
        <Link
          href={`/eign/${fnum}/stilla`}
          className="vm-btn-secondary"
          style={{ textDecoration: "none" }}
        >
          Stilla aftur
        </Link>
        <button className="vm-btn-secondary" disabled style={{ opacity: 0.5 }}>
          Sækja PDF (koma síðar)
        </button>
        <ShareButton packed={sp.a || ""} />
      </section>

      <section
        style={{
          fontSize: "0.82rem",
          color: "var(--vm-ink-faint)",
          lineHeight: 1.55,
          fontStyle: "italic",
        }}
      >
        Persónulegt verðmat er byggt á hardcoded marginal effects í v1 (literature-anchored).
        Sprint 3 refinar þessi gildi með LightGBM partial-dependence plots. Grunnverðmat kemur úr
        model {prediction.model_version} · {prediction.calibration_version}.
      </section>
    </main>
  );
}

function AdjustmentWaterfall({ rows, baselineMean }) {
  const maxAbs = Math.max(...rows.map((r) => Math.abs(r.impact_isk)), 1);
  return (
    <div>
      {rows.map((r, i) => {
        const positive = r.impact_isk >= 0;
        const widthPct = (Math.abs(r.impact_isk) / maxAbs) * 50;
        const displayValue = formatValueLabel(r.question, r.value);
        return (
          <div
            key={i}
            style={{
              display: "grid",
              gridTemplateColumns: "1.3fr 2fr 0.9fr",
              alignItems: "center",
              gap: "1rem",
              padding: "0.55rem 0",
              borderBottom:
                i < rows.length - 1 ? "1px solid var(--vm-border)" : "none",
            }}
          >
            <div>
              <div style={{ fontSize: "0.92rem", color: "var(--vm-ink)" }}>
                {r.label}
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--vm-ink-muted)" }}>
                {displayValue}
              </div>
            </div>
            <div style={{ position: "relative", height: 24 }}>
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  top: 0,
                  bottom: 0,
                  width: 1,
                  background: "var(--vm-border-strong)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  top: 4,
                  bottom: 4,
                  left: positive ? "50%" : `${50 - widthPct}%`,
                  width: `${widthPct}%`,
                  background: positive
                    ? "var(--vm-success)"
                    : "var(--vm-danger)",
                  opacity: 0.85,
                  borderRadius: 3,
                }}
              />
            </div>
            <div
              className="tabular"
              style={{
                textAlign: "right",
                color: positive ? "var(--vm-success)" : "var(--vm-danger)",
                fontWeight: 500,
                fontSize: "0.95rem",
              }}
            >
              {positive ? "+" : ""}
              {formatMillions(r.impact_isk)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function formatValueLabel(question, value) {
  const map = {
    kitchen_renovated: { ja: "Já", nei: "Nei", ovisst: "Ekki viss" },
    bathroom_renovated: { ja: "Já", nei: "Nei", ovisst: "Ekki viss" },
    flooring: {
      parket: "Parket",
      flisar: "Flísar",
      teppi: "Teppi",
      blanda: "Blanda",
    },
    view: {
      sjor: "Sjór",
      fjoll: "Fjöll",
      borg: "Borg",
      gras: "Gras/garður",
      takmarkat: "Takmarkað",
    },
    balcony: {
      engar: "Engar",
      litlar: "Litlar",
      storar: "Stórar",
      verond: "Verönd",
    },
    garage: {
      enginn: "Enginn",
      einstaett: "Einstætt",
      tvofalt: "Tvöfaldur",
      sameign: "Í sameign",
    },
    elevator: { ja: "Já", nei: "Nei", na: "Á ekki við" },
    condition_overall: {
      gott: "Gott",
      medal: "Meðal",
      thorfVidgerd: "Þarf viðgerða",
    },
    floor_position: {
      kjallari: "Kjallari",
      jardhed: "Jarðhæð",
      floor1_3: "1.–3. hæð",
      floor4plus: "4. hæð eða hærra",
      ris: "Rishæð",
    },
    proximity_school: { ja: "Já", nei: "Nei", ovisst: "Ekki viss" },
    proximity_store: { ja: "Já", nei: "Nei", ovisst: "Ekki viss" },
  };
  return map[question]?.[value] || value;
}
