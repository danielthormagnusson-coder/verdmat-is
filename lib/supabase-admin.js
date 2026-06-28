import { createClient } from "@supabase/supabase-js";

// Server-only Supabase client using the service-role key. NEVER import this into
// a client component — SUPABASE_SERVICE_ROLE_KEY is not a NEXT_PUBLIC_ var, so it
// is not bundled to the browser, but importing this module client-side would also
// throw at runtime (serviceKey === undefined). Used by the auth-locked /ops
// operator dashboard to read health tables (pipeline_runs, model_metrics,
// predictions, scraper.*) that anon is intentionally NOT granted SELECT on.
//
// Provision: app/.env.local (local) + Vercel env (prod) must set
//   SUPABASE_SERVICE_ROLE_KEY=<service_role JWT from Supabase dashboard>

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

export function createSupabaseAdmin() {
  if (!url || !serviceKey) {
    throw new Error(
      "createSupabaseAdmin: missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
    );
  }
  return createClient(url, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}
