import { NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

export async function middleware(request) {
  const { pathname } = request.nextUrl;
  // /ops is the internal operator dashboard — gate it behind the same pro_users
  // lock as /pro so the operational signals (run logs, costs, drift) are not
  // served on a known public path.
  if (!pathname.startsWith("/pro") && !pathname.startsWith("/ops")) {
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
