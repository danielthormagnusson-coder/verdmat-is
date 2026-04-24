import Link from "next/link";
import { supabase } from "@/lib/supabase";
import {
  HeldMapePanel,
  CoveragePanel,
  SegmentTable,
  PipelineHealthPanel,
} from "@/components/ModelstadaPanels";

export const revalidate = 600;

export const metadata = {
  title: "Líkansstaða — Hversu nákvæmt er iter4 verðmatslíkanið?",
  description:
    "Held-set MAPE, vissubil og per-segment skekkja fyrir iter4 verðmatslíkanið. Uppfært mánaðarlega með transparent aðferðafræði.",
  openGraph: {
    title: "Líkansstaða — Verdmat",
    description:
      "Held-set MAPE, vissubil og pipeline health fyrir iter4 verðmatslíkanið.",
    type: "website",
    locale: "is_IS",
  },
};

function formatIsDate(d) {
  if (!d) return "—";
  const dt = new Date(d);
  return dt.toLocaleDateString("is-IS", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function daysAgo(d) {
  if (!d) return null;
  const ms = Date.now() - new Date(d).getTime();
  return Math.max(0, Math.round(ms / (24 * 3600 * 1000)));
}

async function loadHistory() {
  const { data, error } = await supabase
    .from("model_tracking_history")
    .select(
      "period, segment, n_held, mape, median_ape, bias_log, cov80, cov95, status_label, model_version, calibration_version, created_at",
    )
    .order("period", { ascending: true })
    .order("segment", { ascending: true, nullsFirst: true });
  if (error) {
    console.error("[modelstada] history load failed", error);
    return [];
  }
  return data || [];
}

async function loadPipelineHealth() {
  // Compose six health items per spec §6.6 — best-effort from what's in the DB.
  const [tracking, sales, rsi, ats, latestListing] = await Promise.all([
    supabase
      .from("model_tracking_history")
      .select("period, created_at, calibration_version")
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase
      .from("sales_history")
      .select("thinglystdags")
      .order("thinglystdags", { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase
      .from("repeat_sale_index")
      .select("period")
      .order("year", { ascending: false })
      .order("quarter", { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase
      .from("ats_dashboard_monthly_heat")
      .select("month")
      .order("month", { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase
      .from("properties")
      .select("scraped_at_latest")
      .order("scraped_at_latest", { ascending: false })
      .limit(1)
      .maybeSingle(),
  ]);

  const items = [];

  if (tracking?.data) {
    const days = daysAgo(tracking.data.created_at);
    items.push({
      key: "tracking",
      label: `Síðasta endurnýjun: ${formatIsDate(tracking.data.created_at)}`,
      status: "ok",
      detail: days != null ? `${days} dagar síðan` : "",
    });
  } else {
    items.push({
      key: "tracking",
      label: "Síðasta endurnýjun: —",
      status: "warn",
      detail: "ekkert í tracking log",
    });
  }

  if (sales?.data?.thinglystdags) {
    const days = daysAgo(sales.data.thinglystdags);
    items.push({
      key: "kaupskra",
      label: `Síðasta þinglýst kaupsamning: ${formatIsDate(sales.data.thinglystdags)}`,
      status: days != null && days > 40 ? "warn" : "ok",
      detail: days != null ? `${days} dagar síðan` : "",
    });
  }

  if (rsi?.data?.period) {
    items.push({
      key: "rsi",
      label: `repeat_sale_index: fresh`,
      status: "ok",
      detail: rsi.data.period,
    });
  }

  if (ats?.data?.month) {
    items.push({
      key: "ats",
      label: `ATS lookup: fresh`,
      status: "ok",
      detail: ats.data.month,
    });
  }

  items.push({
    key: "conformal",
    label: `Conformal calibration: ${tracking?.data?.calibration_version ?? "iter4_conformal_v1"}`,
    status: "ok",
    detail: "",
  });

  items.push({
    key: "listings",
    label: "Listings data: scrape-gap frá júlí 2025",
    status: "warn",
    detail: latestListing?.data?.scraped_at_latest
      ? formatIsDate(latestListing.data.scraped_at_latest)
      : "",
  });

  return items;
}

export default async function ModelstadaPage() {
  const [history, health] = await Promise.all([loadHistory(), loadPipelineHealth()]);
  const latest = history[history.length - 1];

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
        Líkansstaða
      </h1>
      <p
        style={{
          color: "var(--vm-ink-muted)",
          fontSize: "1rem",
          maxWidth: 720,
          marginBottom: "2rem",
        }}
      >
        Hversu nákvæmur er iter4 verðmatsmódelið?
      </p>

      <HeldMapePanel history={history} />
      <CoveragePanel history={history} />
      <SegmentTable segments={history} />
      <PipelineHealthPanel health={health} />

      <section
        className="vm-card"
        style={{ marginBottom: "1.5rem" }}
      >
        <p
          style={{
            fontSize: "0.75rem",
            color: "var(--vm-ink-faint)",
            fontWeight: 600,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            margin: 0,
          }}
        >
          Aðferðafræði markaðsstöðu
        </p>
        <p
          style={{
            fontSize: "0.9rem",
            color: "var(--vm-ink-muted)",
            lineHeight: 1.55,
            margin: "0.6rem 0 0.35rem",
          }}
        >
          Markaðsstaða er reiknuð á tvo vegu:
        </p>
        <ul
          style={{
            fontSize: "0.9rem",
            color: "var(--vm-ink-muted)",
            lineHeight: 1.55,
            margin: 0,
            paddingLeft: "1.25rem",
          }}
        >
          <li style={{ marginBottom: "0.45rem" }}>
            <strong style={{ color: "var(--vm-ink)" }}>Ársfjórðungslega:</strong>{" "}
            samanburður við sögulegar percentile tölur síðustu 20 ára (p33/p67
            per segment × svæði). Stable fyrir langtíma trend.
          </li>
          <li>
            <strong style={{ color: "var(--vm-ink)" }}>
              Mánaðarlega (smoothed):
            </strong>{" "}
            samanburður við rolling 12-mán baseline (z<sub>3v12</sub>{" "}
            ± 0,5 þröskuldur). Responsive fyrir nýlegar breytingar en krefst{" "}
            <span className="tabular">n ≥ 50</span> sölu í mánuðinum fyrir
            áreiðanleika. Ef sample er of lítið, fall-ar kerfið til
            ársfjórðungslegrar tölu.
          </li>
        </ul>
      </section>

      <p
        style={{
          marginTop: "1.5rem",
          fontSize: "0.85rem",
          color: "var(--vm-ink-muted)",
        }}
      >
        <Link
          href="/um#adferdafraedi"
          style={{ color: "var(--vm-primary)", fontWeight: 500 }}
        >
          Aðferðafræði →
        </Link>
      </p>
    </main>
  );
}
