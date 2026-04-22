import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

// Spec §4.6 — back-projection over 12 months for a given fastnum.
// Computes implied_value(t) = pred_mean × index_real[cell, t] / index_real[cell, now]
// with linear interpolation between the enclosing quarters for each month.
// Breaks the line across quarters flagged insufficient_sample.

export const revalidate = 600;

function parsePeriod(year, quarter) {
  // Representative month = middle month of the quarter.
  const midMonth = { 1: 2, 2: 5, 3: 8, 4: 11 }[quarter];
  return new Date(Date.UTC(Number(year), Number(midMonth) - 1, 15));
}

function buildCellIndex(quarterly) {
  // Sort asc and retain { date, idx, insufficient }.
  return quarterly
    .map((q) => ({
      date: parsePeriod(q.year, q.quarter),
      idx: q.index_value_real != null ? Number(q.index_value_real) : null,
      insufficient: q.insufficient_sample === true,
    }))
    .filter((q) => q.idx != null)
    .sort((a, b) => a.date - b.date);
}

function interpolate(timeseries, target) {
  // target: Date; timeseries: [{date, idx, insufficient}] ascending by date.
  if (!timeseries.length) return { idx: null, insufficient: false };
  if (target <= timeseries[0].date)
    return { idx: timeseries[0].idx, insufficient: timeseries[0].insufficient };
  for (let i = 0; i < timeseries.length - 1; i++) {
    const a = timeseries[i];
    const b = timeseries[i + 1];
    if (target >= a.date && target <= b.date) {
      // Break the line if either flanking quarter is insufficient.
      if (a.insufficient || b.insufficient)
        return { idx: null, insufficient: true };
      const t =
        (target.getTime() - a.date.getTime()) /
        (b.date.getTime() - a.date.getTime());
      return { idx: a.idx + (b.idx - a.idx) * t, insufficient: false };
    }
  }
  const last = timeseries[timeseries.length - 1];
  return { idx: last.idx, insufficient: last.insufficient };
}

export async function GET(_req, { params }) {
  const { fastnum } = await params;
  const fnum = Number(fastnum);
  if (!Number.isFinite(fnum))
    return NextResponse.json({ error: "Ógildur fastnúmer" }, { status: 400 });

  const [propRes, predRes] = await Promise.all([
    supabase
      .from("properties")
      .select("fastnum, heimilisfang, postnr, postheiti, canonical_code, region_tier")
      .eq("fastnum", fnum)
      .maybeSingle(),
    supabase
      .from("predictions")
      .select("real_pred_mean, model_version, calibration_version")
      .eq("fastnum", fnum)
      .maybeSingle(),
  ]);
  if (propRes.error || !propRes.data) {
    return NextResponse.json({ error: "Eign ekki fundin" }, { status: 404 });
  }
  const property = propRes.data;
  const prediction = predRes.data;
  if (!prediction || prediction.real_pred_mean == null) {
    return NextResponse.json(
      {
        property,
        prediction: null,
        message: "Engin spá til fyrir þessa eign",
      },
      { status: 200 },
    );
  }

  if (!property.canonical_code || !property.region_tier) {
    return NextResponse.json({ property, prediction, message: "Vantar segment/svæði" }, { status: 200 });
  }

  const { data: quarterly } = await supabase
    .from("repeat_sale_index")
    .select("year, quarter, index_value_real, insufficient_sample")
    .eq("canonical_code", property.canonical_code)
    .eq("region_tier", property.region_tier)
    .order("year", { ascending: true })
    .order("quarter", { ascending: true });

  const ts = buildCellIndex(quarterly || []);
  if (ts.length === 0) {
    return NextResponse.json({
      property,
      prediction,
      message: "Engin vísitala til fyrir þetta segment/svæði",
      monthly_values: [],
    });
  }

  // Twelve monthly points ending at the latest repeat-sale quarter midpoint.
  const anchor = ts[ts.length - 1].date;
  const pred = Number(prediction.real_pred_mean);
  const currentIdx = ts[ts.length - 1].idx;
  const monthly = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(anchor);
    d.setUTCMonth(d.getUTCMonth() - i);
    const { idx, insufficient } = interpolate(ts, d);
    monthly.push({
      month: d.toISOString().slice(0, 7),
      value: idx != null ? pred * (idx / currentIdx) : null,
      insufficient,
    });
  }

  const values = monthly.map((m) => m.value).filter((v) => v != null);
  const hi = values.length ? Math.max(...values) : null;
  const lo = values.length ? Math.min(...values) : null;
  const current = monthly[monthly.length - 1].value;
  const twelveAgo = monthly[0].value;
  const pct =
    current != null && twelveAgo != null && twelveAgo !== 0
      ? (current / twelveAgo - 1) * 100
      : null;

  return NextResponse.json({
    property,
    prediction,
    monthly_values: monthly,
    summary: { current, hi, lo, pct },
  });
}
