import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

const OPS_COOKIE = "ops_session";

// Edge-runtime SHA-256 (Web Crypto). The /ops cookie holds sha256(OPS_PASSWORD); we
// recompute the expected hash from the server-only env var and compare. The password
// itself is never stored in a cookie, never NEXT_PUBLIC, never in the client bundle.
async function sha256hex(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function middleware(request) {
  const { pathname } = request.nextUrl;

  // /ops — internal operator dashboard. Gated by a STANDALONE OPS_PASSWORD cookie
  // (decoupled from the Supabase pro_users lock, 2026-06-28): /ops serves only
  // aggregate operational signals, not per-user pro data, so it gets its own simple
  // password gate. /ops/login (form + server action) is the only open path; it sets
  // an HttpOnly+Secure cookie that we verify here against the env hash.
  if (pathname.startsWith("/ops")) {
    if (pathname.startsWith("/ops/login")) return NextResponse.next();
    const secret = process.env.OPS_PASSWORD;
    const token = request.cookies.get(OPS_COOKIE)?.value;
    if (secret && token && token === (await sha256hex(secret))) {
      return NextResponse.next();
    }
    return NextResponse.redirect(new URL("/ops/login", request.url));
  }

  // /pro — existing Supabase auth + pro_users gate (unchanged).
  if (!pathname.startsWith("/pro")) {
    return NextResponse.next();
  }

  let response = NextResponse.next({ request });
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (list) => {
          list.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          list.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  const { data: proRow } = await supabase
    .from("pro_users")
    .select("role")
    .eq("id", user.id)
    .maybeSingle();

  if (!proRow) {
    const pendingUrl = new URL("/pro/pending", request.url);
    return NextResponse.redirect(pendingUrl);
  }

  return response;
}

export const config = {
  matcher: ["/pro/:path*", "/ops/:path*"],
};
