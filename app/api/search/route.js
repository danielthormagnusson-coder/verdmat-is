import { NextResponse } from "next/server";

// Bug 13 — latency optimization (2026-04-27).
//   * Edge Runtime keeps a warm TCP connection from Vercel edge to Supabase
//     pooler, so cold-start serverless penalty (1-2 s) is gone.
//   * /api/search?q=warm is the cron warm-up endpoint — vercel.json schedules
//     */5 m so pgBouncer + Postgres plan-cache stays hot.
//   * The route mirrors the two SearchAutocomplete code paths: 7-digit fastnum
//     direct lookup, otherwise the grouped RPC. Same JSON shape the client
//     expected before, so SearchAutocomplete's render pipeline is unchanged.
export const runtime = "edge";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const FASTNUM_PATTERN = /^\d{7}$/;
const HEADERS_BASE = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
};

async function rpcGrouped(term, signal) {
  const r = await fetch(
    `${SUPABASE_URL}/rest/v1/rpc/search_properties_grouped`,
    {
      method: "POST",
      headers: { ...HEADERS_BASE, "Content-Type": "application/json" },
      body: JSON.stringify({ term }),
      signal,
    },
  );
  if (!r.ok) return [];
  return r.json();
}

async function fastnumLookup(fnum, signal) {
  const url =
    `${SUPABASE_URL}/rest/v1/properties?` +
    `select=fastnum,heimilisfang,postnr,postheiti,tegund_raw,canonical_code,einflm` +
    `&fastnum=eq.${fnum}&limit=1`;
  const r = await fetch(url, { headers: HEADERS_BASE, signal });
  if (!r.ok) return null;
  const arr = await r.json();
  return Array.isArray(arr) && arr.length > 0 ? arr[0] : null;
}

export async function GET(req) {
  const { searchParams } = new URL(req.url);
  const q = (searchParams.get("q") || "").trim();

  // Cron warm-up — fire one cheap RPC + skip caching.
  if (q === "warm") {
    try {
      await rpcGrouped("warm", req.signal);
    } catch (e) {
      // Eat — warm-up should never error the cron job.
    }
    return NextResponse.json(
      { ok: true, warmed: true, ts: Date.now() },
      { headers: { "Cache-Control": "no-store" } },
    );
  }

  if (q.length < 2) {
    return NextResponse.json([], { headers: { "Cache-Control": "no-store" } });
  }

  try {
    if (FASTNUM_PATTERN.test(q)) {
      const d = await fastnumLookup(Number(q), req.signal);
      if (!d) return NextResponse.json([]);
      return NextResponse.json([
        {
          heimilisfang: d.heimilisfang,
          postnr: d.postnr,
          postheiti: d.postheiti,
          n_units: 1,
          anchor_fastnum: d.fastnum,
          tegund_summary: d.tegund_raw || null,
          _prefetchedUnit: {
            fastnum: d.fastnum,
            tegund_raw: d.tegund_raw,
            canonical_code: d.canonical_code,
            einflm: d.einflm,
          },
        },
      ]);
    }
    const data = await rpcGrouped(q, req.signal);
    return NextResponse.json(data || []);
  } catch (e) {
    if (e?.name === "AbortError") {
      return new NextResponse(null, { status: 499 }); // client closed request
    }
    return NextResponse.json(
      { error: String(e) },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }
}
