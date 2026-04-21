import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";
import effects from "@/data/manual_q_effects.json";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request) {
  let body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }
  const { fastnum, answers } = body || {};
  if (!Number.isFinite(Number(fastnum))) {
    return NextResponse.json({ error: "fastnum required" }, { status: 400 });
  }

  const { data: prediction, error } = await supabase
    .from("predictions")
    .select(
      "fastnum, real_pred_mean, real_pred_median, real_pred_lo80, real_pred_hi80, real_pred_lo95, real_pred_hi95, segment, model_version, calibration_version"
    )
    .eq("fastnum", Number(fastnum))
    .maybeSingle();
  if (error || !prediction) {
    return NextResponse.json(
      { error: "Prediction not found for this fastnum" },
      { status: 404 }
    );
  }

  const baseline = {
    mean: Number(prediction.real_pred_mean),
    median: Number(prediction.real_pred_median),
    lo80: Number(prediction.real_pred_lo80),
    hi80: Number(prediction.real_pred_hi80),
    lo95: Number(prediction.real_pred_lo95),
    hi95: Number(prediction.real_pred_hi95),
  };

  let logAdjustment = 0;
  const breakdown = [];
  const qMap = effects.questions || {};

  for (const [question, value] of Object.entries(answers || {})) {
    const q = qMap[question];
    if (!q || value == null) continue;
    const e = q.effects?.[value];
    if (typeof e !== "number" || e === 0) {
      if (typeof e === "number") {
        breakdown.push({
          question,
          label: q.label,
          value,
          effect: 0,
          impact_isk: 0,
        });
      }
      continue;
    }
    logAdjustment += Math.log(1 + e);
    const impact = baseline.mean * e;
    breakdown.push({
      question,
      label: q.label,
      value,
      effect: e,
      impact_isk: Math.round(impact),
    });
  }

  const multiplier = Math.exp(logAdjustment);
  const adjusted = {
    mean: Math.round(baseline.mean * multiplier),
    median: Math.round(baseline.median * multiplier),
    lo80: Math.round(baseline.lo80 * multiplier),
    hi80: Math.round(baseline.hi80 * multiplier),
    lo95: Math.round(baseline.lo95 * multiplier),
    hi95: Math.round(baseline.hi95 * multiplier),
  };

  breakdown.sort((a, b) => Math.abs(b.impact_isk) - Math.abs(a.impact_isk));

  return NextResponse.json({
    baseline,
    adjusted,
    breakdown,
    multiplier,
    model: {
      version: prediction.model_version,
      calibration: prediction.calibration_version,
      segment: prediction.segment,
    },
  });
}
