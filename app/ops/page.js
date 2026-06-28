import { createSupabaseAdmin } from "@/lib/supabase-admin";

// Internal operator dashboard. Service-role read (server-only), auth-locked via
// middleware (pro_users). NOT public — keep out of nav, keep noindex.
// force-dynamic: render fresh per request (ops board wants live signals) and
// avoid build-time prerender calling the service-role DB before env is set.
export const dynamic = "force-dynamic";
export const metadata = {
  title: "Rekstrarstaða — /ops",
  robots: { index: false, follow: false },
};

// ─── Config: expected freshness windows (hours) per signal ───────────────────
// green ≤ warnH · amber ≤ failH · red beyond (or missing).
const OPS_CONFIG = {
  extractionCap: 200, // nightly forward-extraction N cap (hardcoded in scraper, not in DB)
  evalDailyBudgetUsd: 10, // model_quality_eval / extraction Haiku budget guard
  daily: { warnH: 28, failH: 52 }, // nightly chains
  monthly: { warnH: 24 * 35, failH: 24 * 45 }, // precompute batch (predictions/comps/properties)
  sales: { warnH: 24 * 5, failH: 24 * 14 }, // HMS daily-fresh, csv load manually gated
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function ageHours(ts) {
  if (!ts) return null;
  return (Date.now() - new Date(ts).getTime()) / 3.6e6;
}
function fmtAge(hours) {
  if (hours == null) return "—";
  if (hours < 48) return `${Math.round(hours)} klst`;
  return `${Math.round(hours / 24)} d`;
}
function fmtTs(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("is-IS", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: "UTC",
  });
}
function freshLevel(hours, cfg) {
  if (hours == null) return "red";
  if (hours <= cfg.warnH) return "green";
  if (hours <= cfg.failH) return "amber";
  return "red";
}
const LEVEL_COLOR = { green: "var(--vm-success)", amber: "var(--vm-accent)", red: "var(--vm-danger)" };
function Dot({ level }) {
  return (
    <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 999, background: LEVEL_COLOR[level] || "var(--vm-neutral)", marginRight: 8, verticalAlign: "middle" }} />
  );
}
function val(settled) {
  return settled.status === "fulfilled" ? settled.value : null;
}

async function loadOps() {
  const db = createSupabaseAdmin();
  const top = (q) => q.limit(1).maybeSingle();

  const [runs, salesMax, predMax, propsMax, compsMax, metricRow, scsRes] = await Promise.allSettled([
    db.from("pipeline_runs").select("run_type,exit_status,started_at,ended_at,summary").order("started_at", { ascending: false }).limit(40),
    top(db.from("sales_history").select("thinglystdags").order("thinglystdags", { ascending: false })),
    top(db.from("predictions").select("predicted_at,model_version,calibration_version").order("predicted_at", { ascending: false })),
    top(db.from("properties").select("scraped_at_latest").order("scraped_at_latest", { ascending: false })),
    top(db.from("comps_index").select("last_sale_date").order("last_sale_date", { ascending: false })),
    top(db.from("model_metrics").select("model_version,mape,med_ape,bias,cov80,cov95,oos_cutoff,n_pairs,computed_at").eq("segment_dim", "overall").eq("sample_scope", "all_oos").eq("score_type", "baseline").order("computed_at", { ascending: false })),
    // scraper.* lives in a non-REST-exposed schema → read aggregate-only via SECURITY DEFINER RPC.
    db.rpc("ops_scraper_signals"),
  ]);

  const runsData = val(runs)?.data || [];
  const latestByType = {};
  for (const r of runsData) if (!latestByType[r.run_type]) latestByType[r.run_type] = r;

  const scsSettled = val(scsRes);
  const scs = scsSettled?.data || null;
  const scsErr = scsSettled?.error || (scsRes.status === "rejected" ? scsRes.reason : null);
  const chain = scs?.chain || {};

  return {
    scsErr,
    latestByType,
    chain,
    fresh: {
      listings: chain.mbl_last_seen || chain.myigloo_last_seen,
      priceHist: chain.price_history_max,
      extraction: chain.extraction_max,
      valuation: chain.valuation_max,
      sales: val(salesMax)?.data?.thinglystdags,
      predictions: val(predMax)?.data?.predicted_at,
      modelMetrics: val(metricRow)?.data?.computed_at,
      properties: val(propsMax)?.data?.scraped_at_latest,
      comps: val(compsMax)?.data?.last_sale_date,
    },
    predMeta: val(predMax)?.data,
    extraction: scs?.extraction || null,
    backlog: scs?.backlog || null,
    sources: scs?.sources || null,
    model: val(metricRow)?.data,
    evalSummary: latestByType["model_quality_eval"]?.summary || null,
  };
}

// ─── UI primitives ───────────────────────────────────────────────────────────
function Card({ title, children, sub }) {
  return (
    <section className="vm-card" style={{ marginBottom: "1.25rem", padding: "1.1rem 1.25rem" }}>
      <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--vm-ink-faint)", marginBottom: sub ? 2 : 10 }}>{title}</div>
      {sub && <div style={{ fontSize: "0.78rem", color: "var(--vm-ink-faint)", marginBottom: 10 }}>{sub}</div>}
      {children}
    </section>
  );
}
const th = { textAlign: "left", fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--vm-ink-faint)", padding: "4px 10px 6px 0", fontWeight: 600 };
const td = { padding: "5px 10px 5px 0", fontSize: "0.85rem", color: "var(--vm-ink)", borderTop: "1px solid var(--vm-border)", whiteSpace: "nowrap" };

function FreshRow({ label, ts, cfg, note }) {
  const h = ageHours(ts);
  const level = freshLevel(h, cfg);
  return (
    <tr>
      <td style={td}><Dot level={level} />{label}</td>
      <td style={{ ...td, fontFamily: "var(--font-mono)" }} className="tabular">{ts ? fmtTs(ts) : "—"}</td>
      <td style={{ ...td, fontFamily: "var(--font-mono)", color: LEVEL_COLOR[level], fontWeight: 600 }} className="tabular">{fmtAge(h)}</td>
      <td style={{ ...td, color: "var(--vm-ink-muted)", fontSize: "0.78rem", whiteSpace: "normal" }}>{note || ""}</td>
    </tr>
  );
}

function runLevel(r) {
  if (!r) return { level: "red", txt: "engin keyrsla" };
  if (r.exit_status === "success") return { level: "green", txt: "success" };
  // monthly_cpi_reanchor failing on the sanity guard is intended behaviour, not a fault
  if (r.run_type === "monthly_cpi_reanchor" && r.summary?.reason && /column/i.test(r.summary.reason)) {
    return { level: "amber", txt: "sanity-halt (vörn virk)" };
  }
  return { level: "red", txt: r.exit_status || "?" };
}

export default async function OpsPage() {
  let data, fatal;
  try { data = await loadOps(); } catch (e) { fatal = e.message; }

  if (fatal) {
    return (
      <main className="vm-container" style={{ padding: "2.5rem 0 4rem" }}>
        <h1 className="display" style={{ fontSize: "1.8rem" }}>/ops</h1>
        <div className="vm-card" style={{ borderColor: "var(--vm-danger)", color: "var(--vm-danger)" }}>
          Service-role tenging mistókst: {fatal}
          <div style={{ color: "var(--vm-ink-muted)", marginTop: 8, fontSize: "0.85rem" }}>
            Vantar líklega <code>SUPABASE_SERVICE_ROLE_KEY</code> í env (app/.env.local lókalt, Vercel í prod).
          </div>
        </div>
      </main>
    );
  }

  const { latestByType, chain, fresh, predMeta, extraction, backlog, sources, model, evalSummary, scsErr } = data;
  const predAge = ageHours(fresh.predictions);
  const predRed = freshLevel(predAge, OPS_CONFIG.monthly) === "red";
  const fastnumPct = sources?.total ? Math.round((100 * sources.fastnum_filled) / sources.total) : null;

  const RUN_LABELS = {
    monthly: "monthly (anchor/CPI precompute)",
    monthly_cpi_reanchor: "monthly_cpi_reanchor",
    daily_sales_refresh: "daily_sales_refresh",
    model_quality_eval: "model_quality_eval",
  };
  const runTypes = ["daily_sales_refresh", "model_quality_eval", "monthly_cpi_reanchor", "monthly"];

  return (
    <main className="vm-container" style={{ padding: "2rem 0 4rem", maxWidth: 1000 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "1.5rem", flexWrap: "wrap", gap: 8 }}>
        <h1 className="display" style={{ fontSize: "1.9rem", margin: 0 }}>Rekstrarstaða · /ops</h1>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", color: "var(--vm-ink-faint)" }} className="tabular">
          {fmtTs(new Date().toISOString())} UTC · per-request · innra (auth-læst)
        </span>
      </div>

      {predRed && (
        <div className="vm-card" style={{ marginBottom: "1.25rem", borderColor: "var(--vm-danger)", background: "rgba(176,78,78,0.06)" }}>
          <strong style={{ color: "var(--vm-danger)" }}>🔴 Verðmöt staðnað</strong>{" "}
          <span style={{ color: "var(--vm-ink-muted)", fontSize: "0.9rem" }}>
            Nýjasta predictions-batch er <strong>{fresh.predictions || "—"}</strong> ({fmtAge(predAge)} gamalt) — precompute-pipeline hefur ekki keyrt. Síðan birtir gömul verðmöt.
          </span>
        </div>
      )}

      {/* SPJALD 2 — FERSKLEIKI (kjarni, efst) */}
      <Card title="Ferskleiki gagna" sub="nýjasti tímastimpill per lykiltöflu vs núna (UTC)">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr><th style={th}>Tafla</th><th style={th}>Nýjast</th><th style={th}>Aldur</th><th style={th}>Athugasemd</th></tr></thead>
          <tbody>
            <FreshRow label="predictions (verðmöt)" ts={fresh.predictions} cfg={OPS_CONFIG.monthly} note={predRed ? "mánaðarleg endurnýjun — 2 cyclar misstir" : "mánaðarleg"} />
            <FreshRow label="properties (HMS metadata)" ts={fresh.properties} cfg={OPS_CONFIG.monthly} note="endurnýjað með precompute" />
            <FreshRow label="comps_index" ts={fresh.comps} cfg={OPS_CONFIG.monthly} note="endurnýjað með precompute" />
            <FreshRow label="model_metrics (VÉL 1 einkunn)" ts={fresh.modelMetrics} cfg={OPS_CONFIG.daily} note="model_quality_eval skrifar" />
            <FreshRow label="sales_history (kaupskrá)" ts={fresh.sales} cfg={OPS_CONFIG.sales} note="HMS dagleg; csv-load handvirk" />
            <FreshRow label="scraper.listings" ts={fresh.listings} cfg={OPS_CONFIG.daily} note="nætur-skröpun" />
            <FreshRow label="listing_price_history" ts={fresh.priceHist} cfg={OPS_CONFIG.daily} note="verðbreytingar" />
            <FreshRow label="listing_extractions" ts={fresh.extraction} cfg={OPS_CONFIG.daily} note="forward extraction" />
            <FreshRow label="listing_valuations" ts={fresh.valuation} cfg={OPS_CONFIG.daily} note="expected-vs-real" />
          </tbody>
        </table>
      </Card>

      {/* SPJALD 1A — BATCH-KEYRSLUR */}
      <Card title="Nætur-keðja · batch-keyrslur" sub="pipeline_runs — nýjasta keyrsla per run_type">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr><th style={th}>run_type</th><th style={th}>Staða</th><th style={th}>Hófst</th><th style={th}>Lengd</th><th style={th}>Lykil-summary</th></tr></thead>
          <tbody>
            {runTypes.map((rt) => {
              const r = latestByType[rt];
              const { level, txt } = runLevel(r);
              const dur = r?.ended_at && r?.started_at ? Math.round((new Date(r.ended_at) - new Date(r.started_at)) / 1000) : null;
              const sum = r?.summary || {};
              const keys = Object.keys(sum).filter((k) => typeof sum[k] !== "object").slice(0, 3);
              return (
                <tr key={rt}>
                  <td style={td}><Dot level={level} />{RUN_LABELS[rt] || rt}</td>
                  <td style={{ ...td, color: LEVEL_COLOR[level], fontWeight: 600 }}>{txt}</td>
                  <td style={{ ...td, fontFamily: "var(--font-mono)" }} className="tabular">{r ? fmtTs(r.started_at) : "—"}</td>
                  <td style={{ ...td, fontFamily: "var(--font-mono)" }} className="tabular">{dur != null ? `${dur}s` : "—"}</td>
                  <td style={{ ...td, fontSize: "0.75rem", color: "var(--vm-ink-muted)", whiteSpace: "normal", fontFamily: "var(--font-mono)" }}>
                    {keys.map((k) => `${k}=${sum[k]}`).join(" · ") || "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      {/* SPJALD 1B — SKRÖPUNAR-KEÐJA (afleidd) */}
      <Card title="Nætur-keðja · skröpun (afleitt af ferskleika)" sub="fetch/parse/promote/extraction eru ekki í pipeline_runs — staða leidd af gagna-tímastimplum gegnum ops_scraper_signals(), vænt dagleg cadence">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr><th style={th}>Þrep</th><th style={th}>Síðast</th><th style={th}>Aldur</th><th style={th}>Vænt</th></tr></thead>
          <tbody>
            <FreshRow label="mbl fetch" ts={chain.mbl_last_seen} cfg={OPS_CONFIG.daily} note="~01:00" />
            <FreshRow label="myigloo fetch" ts={chain.myigloo_last_seen} cfg={OPS_CONFIG.daily} note="~02:00" />
            <FreshRow label="canonical promote" ts={chain.canonical_last_promoted} cfg={OPS_CONFIG.daily} note="~02:00" />
            <FreshRow label="forward extraction" ts={chain.extraction_max} cfg={OPS_CONFIG.daily} note="~01:00" />
            <FreshRow label="forward valuation" ts={chain.valuation_max} cfg={OPS_CONFIG.daily} note="~01:00" />
          </tbody>
        </table>
      </Card>

      {/* SPJALD 4 — MÓDEL */}
      <Card title="Módel · VÉL 1 einkunn" sub="model_metrics — nýjasta overall / all_oos / baseline">
        {model ? (
          <div style={{ display: "flex", gap: 18, flexWrap: "wrap", alignItems: "flex-end" }}>
            {[
              ["MAPE", `${(+model.mape).toFixed(1)}%`, model.mape <= 15 ? "green" : model.mape <= 18 ? "amber" : "red"],
              ["medAPE", `${(+model.med_ape).toFixed(1)}%`, "green"],
              ["bias", `${(+model.bias).toFixed(1)}%`, Math.abs(model.bias) <= 3 ? "green" : "amber"],
              ["cov80", `${(+model.cov80).toFixed(0)}%`, model.cov80 >= 77 ? "green" : "amber"],
              ["cov95", `${(+model.cov95).toFixed(0)}%`, model.cov95 >= 92 ? "green" : "amber"],
            ].map(([k, v, lvl]) => (
              <div key={k}>
                <div style={{ fontSize: "0.7rem", color: "var(--vm-ink-faint)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{k}</div>
                <div className="tabular" style={{ fontSize: "1.4rem", fontWeight: 600, color: LEVEL_COLOR[lvl] || "var(--vm-ink)" }}>{v}</div>
              </div>
            ))}
            <div style={{ marginLeft: "auto", textAlign: "right", fontSize: "0.78rem", color: "var(--vm-ink-muted)" }}>
              <div>{model.model_version} · N={model.n_pairs}</div>
              <div>OOS cutoff {String(model.oos_cutoff)} · {fmtTs(model.computed_at)}</div>
              <div style={{ color: predRed ? "var(--vm-danger)" : "var(--vm-ink-muted)" }}>
                predictions-batch: <strong>{fresh.predictions}</strong>{predRed ? " 🔴" : ""} ({predMeta?.model_version})
              </div>
            </div>
          </div>
        ) : <span style={{ color: "var(--vm-ink-muted)" }}>engin gögn</span>}
        <div style={{ fontSize: "0.75rem", color: "var(--vm-ink-faint)", marginTop: 10 }}>
          cov80 markmið 80% / cov95 markmið 95% — undir = intervalar of þröngir á nýlegri sölu.
        </div>
      </Card>

      {/* SPJALD 3 — EXTRACTION */}
      <Card title="Extraction" sub="forward LLM-extraction — síðasti keyrslu-dagur (þak hardcoded í scraper)">
        {extraction ? (
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <Metric label="extraction (síð. dagur)" value={`${extraction.count_latest_day ?? "—"} / ${OPS_CONFIG.extractionCap}`} level={extraction.count_latest_day >= OPS_CONFIG.extractionCap ? "amber" : "green"} sub={extraction.count_latest_day >= OPS_CONFIG.extractionCap ? "á þaki" : "undir þaki"} />
            <Metric label="valuations (síð. dagur)" value={extraction.val_count_latest_day ?? "—"} level="green" />
            <Metric label="backlog (óunnar íbúðir)" value={backlog?.unprocessed ?? "—"} level={backlog?.unprocessed > 5000 ? "amber" : "green"} sub={backlog ? `af ${backlog.live_res_sale} virkum · ${backlog.live_res_sale_valued} unnar` : ""} />
            <Metric label="model" value={extraction.model || "—"} level="green" />
            <Metric label="schema v." value={extraction.schema_version || "—"} level="green" />
          </div>
        ) : <span style={{ color: "var(--vm-ink-muted)" }}>engin gögn (RPC?)</span>}
        <div style={{ fontSize: "0.78rem", color: "var(--vm-ink-muted)", marginTop: 12, lineHeight: 1.5 }}>
          <strong>$-kostnaður: ekki loggað í DB.</strong> listing_extractions hefur engan kostnaðar-dálk. Næsta best:
          model_quality_eval Haiku-kostnaður = <span className="tabular">{evalSummary?.paired_summary?.cost_est_usd != null ? `$${(+evalSummary.paired_summary.cost_est_usd).toFixed(2)}` : "—"}</span> síðustu eval-keyrslu (þak ${OPS_CONFIG.evalDailyBudgetUsd}/dag).
          Backlog = virkar íbúða-söluauglýsingar án verðmats (extraction→valuation join).
        </div>
      </Card>

      {/* SPJALD 5 — SCRAPER-HEIMILDIR */}
      <Card title="Skröpunar-heimildir" sub="scraper.listings_canonical (gegnum ops_scraper_signals())">
        {sources ? (
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <Metric label="mbl (canonical)" value={sources.mbl ?? 0} level="green" sub="nætur-delta" />
            <Metric label="myigloo" value={sources.myigloo ?? 0} level="green" sub="nætur-fullt" />
            <Metric label="visir" value={sources.visir ?? 0} level={sources.visir ? "amber" : "amber"} sub="seed only · engin nætur-refresh" />
            <Metric label="virk (ekki withdrawn)" value={sources.live ?? "—"} level="green" sub={`${sources.withdrawn ?? 0} withdrawn`} />
            <Metric label="fastnum-þekja" value={fastnumPct != null ? `${fastnumPct}%` : "—"} level={fastnumPct >= 95 ? "green" : "amber"} sub={`${sources.fastnum_filled ?? "—"} / ${sources.total ?? "—"}`} />
          </div>
        ) : <span style={{ color: "var(--vm-ink-muted)" }}>engin gögn (RPC?)</span>}
      </Card>

      {scsErr && (
        <div className="vm-card" style={{ borderColor: "var(--vm-accent)", color: "var(--vm-ink-muted)", fontSize: "0.8rem" }}>
          ⚠ ops_scraper_signals() skilaði villu: <code>{String(scsErr.message || scsErr)}</code> — scraper-spjöld (1B, extraction, heimildir) tóm. Public-spjöld standa.
        </div>
      )}
    </main>
  );
}

function Metric({ label, value, level, sub }) {
  return (
    <div>
      <div style={{ fontSize: "0.7rem", color: "var(--vm-ink-faint)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div className="tabular" style={{ fontSize: "1.3rem", fontWeight: 600, color: LEVEL_COLOR[level] || "var(--vm-ink)" }}>{value}</div>
      {sub && <div style={{ fontSize: "0.72rem", color: "var(--vm-ink-faint)" }}>{sub}</div>}
    </div>
  );
}
