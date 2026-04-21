// Landing + drill-down dashboard data fetchers.
// Server-only; executed during ISR render with revalidate = 600.

import { supabase } from "@/lib/supabase";

const MAIN_RESIDENTIAL_SEGMENTS = [
  "APT_FLOOR",
  "APT_STANDARD",
  "SFH_DETACHED",
  "ROW_HOUSE",
];
const MAIN_REGIONS = ["RVK_core", "Capital_sub", "Country"];

// Hero A + Card 2: single pooled view.
async function fetchMainPooled() {
  const { data, error } = await supabase
    .from("repeat_sale_index_main_pooled")
    .select("*")
    .order("year", { ascending: true })
    .order("quarter", { ascending: true });
  if (error) throw error;
  return data || [];
}

// Hero B: regime per cell.
async function fetchLatestRegime() {
  const { data, error } = await supabase
    .from("latest_regime_per_cell")
    .select("*");
  if (error) throw error;
  return data || [];
}

// Card 1: weighted 3-mo above_list_rate from monthly heat table.
async function fetchAboveListPooled3mo() {
  const { data, error } = await supabase
    .from("ats_dashboard_monthly_heat")
    .select("month, canonical_code, region_tier, above_list_rate, n_month")
    .in("canonical_code", MAIN_RESIDENTIAL_SEGMENTS)
    .in("region_tier", MAIN_REGIONS)
    .order("month", { ascending: false });
  if (error) throw error;
  return data || [];
}

// Card 3: latest tracking row for RESIDENTIAL_EX_SUMMER segment.
async function fetchLatestMape() {
  const { data, error } = await supabase
    .from("model_tracking_history")
    .select("period, segment, n_held, mape, cov80, cov95, status_label")
    .eq("segment", "RESIDENTIAL_EX_SUMMER")
    .order("period", { ascending: false })
    .limit(1);
  if (error) throw error;
  return (data || [])[0] || null;
}

// Timeline: 3 segments pooled across regions.
async function fetchBySegment() {
  const pageSize = 1000;
  let all = [];
  for (let from = 0; from < 10000; from += pageSize) {
    const to = from + pageSize - 1;
    const { data, error } = await supabase
      .from("repeat_sale_index_by_segment")
      .select("*")
      .order("canonical_code", { ascending: true })
      .order("year", { ascending: true })
      .order("quarter", { ascending: true })
      .range(from, to);
    if (error || !data || data.length === 0) break;
    all = all.concat(data);
    if (data.length < pageSize) break;
  }
  return all;
}

// Summarize hero A from pooled rows.
function computeHeroA(pooled) {
  const valid = pooled.filter((r) => r.index_real != null);
  if (valid.length < 5) return { pct: null, current: null, prior: null };
  const last = valid[valid.length - 1];
  const prior = valid[valid.length - 5]; // 4 quarters back = 12 months
  if (!prior || prior.index_real == null) {
    return { pct: null, current: last.index_real, prior: null };
  }
  const pct = (Number(last.index_real) / Number(prior.index_real) - 1) * 100;
  return {
    pct,
    current: Number(last.index_real),
    currentPeriod: last.period,
    prior: Number(prior.index_real),
    priorPeriod: prior.period,
  };
}

// Aggregate regime pill. Rule: >=8 of 12 cells hot/cold → labeled, else neutral.
function computeHeroB(rows) {
  const expected = MAIN_RESIDENTIAL_SEGMENTS.length * MAIN_REGIONS.length; // 12
  const counts = { hot: 0, neutral: 0, cold: 0, unknown: 0 };
  for (const r of rows) counts[r.heat_bucket ?? "unknown"] += 1;
  let pill = "HLUTLAUS";
  if (counts.hot >= 8) pill = "HEITUR";
  else if (counts.cold >= 8) pill = "KALDUR";
  return { pill, counts, nTotal: expected };
}

// Card 1 value — weighted above_list_rate across main residential cells for
// the last 3 distinct months in the monthly_heat table.
function computeCard1(rows) {
  if (!rows.length) return null;
  const months = Array.from(new Set(rows.map((r) => r.month))).sort().reverse().slice(0, 3);
  const selected = rows.filter((r) => months.includes(r.month));
  let weightedSum = 0;
  let totalN = 0;
  for (const r of selected) {
    if (r.above_list_rate == null || r.n_month == null) continue;
    weightedSum += Number(r.above_list_rate) * Number(r.n_month);
    totalN += Number(r.n_month);
  }
  if (totalN === 0) return null;
  return { pct: (weightedSum / totalN) * 100, months, n: totalN };
}

// Card 2 — 10yr CAGR from the 40-quarter lookback on the pooled view.
function computeCard2(pooled) {
  const valid = pooled.filter((r) => r.index_real != null);
  if (valid.length < 40) return null;
  const last = valid[valid.length - 1];
  const tenYearsAgo = valid[valid.length - 40];
  if (!tenYearsAgo || tenYearsAgo.index_real == null) return null;
  const ratio = Number(last.index_real) / Number(tenYearsAgo.index_real);
  const cagr = (Math.pow(ratio, 1 / 10) - 1) * 100;
  return { pct: cagr, fromPeriod: tenYearsAgo.period, toPeriod: last.period };
}

// Timeline: pivot rows into { period, [seg]: index_real } for Recharts.
function pivotTimeline(rows) {
  const byPeriod = new Map();
  for (const r of rows) {
    if (r.index_real == null) continue;
    const key = `${r.year}Q${r.quarter}`;
    if (!byPeriod.has(key)) {
      byPeriod.set(key, {
        period: key,
        year: r.year,
        quarter: r.quarter,
        _sortKey: r.year * 4 + r.quarter,
      });
    }
    byPeriod.get(key)[r.canonical_code] = Number(r.index_real);
  }
  return Array.from(byPeriod.values()).sort((a, b) => a._sortKey - b._sortKey);
}

export async function loadLandingData() {
  const [pooled, regime, above, mape, bySeg] = await Promise.all([
    fetchMainPooled(),
    fetchLatestRegime(),
    fetchAboveListPooled3mo(),
    fetchLatestMape(),
    fetchBySegment(),
  ]);

  return {
    heroA: computeHeroA(pooled),
    heroB: computeHeroB(regime),
    card1: computeCard1(above),
    card2: computeCard2(pooled),
    card3: mape,
    timeline: pivotTimeline(bySeg),
  };
}
