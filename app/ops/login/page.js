import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import crypto from "node:crypto";

// Password gate for the internal /ops dashboard. Server-only: the password is compared
// against process.env.OPS_PASSWORD (NEVER NEXT_PUBLIC, never shipped to the client). On a
// match we set an HttpOnly+Secure cookie holding sha256(OPS_PASSWORD); middleware verifies
// it against the same env hash. force-dynamic so the server action + cookie write run fresh.
export const dynamic = "force-dynamic";
export const metadata = {
  title: "/ops — innskráning",
  robots: { index: false, follow: false },
};

const OPS_COOKIE = "ops_session";

async function login(formData) {
  "use server";
  const submitted = String(formData.get("password") ?? "");
  const expected = process.env.OPS_PASSWORD ?? "";
  // Constant-time compare of equal-length SHA-256 digests (avoids the length-leak and the
  // throw that timingSafeEqual raises on unequal-length buffers).
  const digest = (s) => crypto.createHash("sha256").update(s, "utf8").digest();
  const ok = expected.length > 0 && crypto.timingSafeEqual(digest(submitted), digest(expected));
  if (!ok) {
    redirect("/ops/login?error=1");
  }
  const token = crypto.createHash("sha256").update(expected, "utf8").digest("hex");
  const jar = await cookies();
  jar.set(OPS_COOKIE, token, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/ops",
    maxAge: 60 * 60 * 12, // 12h
  });
  redirect("/ops");
}

export default async function OpsLogin({ searchParams }) {
  const sp = (await searchParams) || {};
  const hasError = Boolean(sp.error);
  return (
    <main className="vm-container" style={{ padding: "4rem 0 6rem", maxWidth: 420 }}>
      <h1 className="display" style={{ fontSize: "1.6rem", marginBottom: "0.4rem" }}>Rekstrarstaða · /ops</h1>
      <p style={{ color: "var(--vm-ink-faint)", fontSize: "0.85rem", marginBottom: "1.25rem" }}>
        Innra rekstrarborð — leyniorðs-varið.
      </p>
      <form
        action={login}
        className="vm-card"
        style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: 12 }}
      >
        <label style={{ fontSize: "0.78rem", color: "var(--vm-ink-faint)" }}>
          Leyniorð
          <input
            type="password"
            name="password"
            autoFocus
            autoComplete="current-password"
            style={{
              width: "100%", marginTop: 6, padding: "0.6rem 0.7rem",
              border: "1px solid var(--vm-border)", borderRadius: 8, fontSize: "0.95rem",
              boxSizing: "border-box",
            }}
          />
        </label>
        {hasError && (
          <div style={{ color: "var(--vm-danger)", fontSize: "0.82rem" }}>Rangt leyniorð.</div>
        )}
        <button
          type="submit"
          style={{
            padding: "0.6rem 1rem", border: "none", borderRadius: 8, cursor: "pointer",
            background: "var(--vm-ink)", color: "var(--vm-bg, #fff)", fontWeight: 600, fontSize: "0.9rem",
          }}
        >
          Skrá inn
        </button>
      </form>
    </main>
  );
}
