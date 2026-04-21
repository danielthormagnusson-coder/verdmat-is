import Link from "next/link";
import { createSupabaseServer } from "@/lib/supabase-server";
import { formatMillions, formatSegment } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Pro dashboard — verdmat.is",
};

export default async function ProDashboard() {
  const supabase = await createSupabaseServer();
  const { data: { user } } = await supabase.auth.getUser();

  const [{ data: proRow }, { data: saved }, { data: valuations }] =
    await Promise.all([
      supabase
        .from("pro_users")
        .select("full_name, role, company")
        .eq("id", user.id)
        .maybeSingle(),
      supabase
        .from("saved_properties")
        .select("fastnum, saved_at, property:fastnum (heimilisfang, postnr, postheiti, canonical_code, einflm, first_photo_url)")
        .eq("user_id", user.id)
        .order("saved_at", { ascending: false })
        .limit(12),
      supabase
        .from("saved_valuations")
        .select("id, fastnum, adjusted_mean, baseline_mean, created_at, property:fastnum (heimilisfang, canonical_code)")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(10),
    ]);

  const roleLabel = {
    banki: "Banki",
    fasteignasali: "Fasteignasali",
    admin: "Admin",
    test: "Test",
  }[proRow?.role] || "Pro";

  return (
    <main className="vm-container" style={{ padding: "3rem 0 4rem" }}>
      <section style={{ marginBottom: "2.5rem" }}>
        <p
          style={{
            fontSize: "0.85rem",
            color: "var(--vm-accent)",
            fontWeight: 600,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            marginBottom: "0.75rem",
          }}
        >
          PRO DASHBOARD
        </p>
        <h1 className="display" style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>
          Velkominn{proRow?.full_name ? `, ${proRow.full_name}` : ""}
        </h1>
        <div
          style={{
            display: "flex",
            gap: "0.75rem",
            alignItems: "center",
            color: "var(--vm-ink-muted)",
          }}
        >
          <span className="vm-badge vm-badge-cold">{roleLabel}</span>
          {proRow?.company && <span>{proRow.company}</span>}
          <span style={{ color: "var(--vm-ink-faint)" }}>· {user.email}</span>
        </div>
      </section>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "1rem",
          marginBottom: "3rem",
        }}
      >
        <CtaCard
          href="/"
          title="Nýtt verðmat"
          body="Leitaðu að eign og fáðu persónulegt verðmat með spurningalista."
          accent
        />
        <CtaCard
          href="/markadur"
          title="Markaðsyfirlit"
          body="Heitir og kaldir reitir, repeat-sale vísitala, segment breakdown."
        />
        <CtaCard
          href="/pro/searches"
          title="Vistuð leit"
          body="Sjá breytingar á markaðnum í valinn hverfi eða segment."
        />
      </section>

      <section style={{ marginBottom: "3rem" }}>
        <h2 className="display" style={{ fontSize: "1.6rem", marginBottom: "1rem" }}>
          Vistaðar eignir
        </h2>
        {saved && saved.length ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
            {saved.map((s) => (
              <Link key={s.fastnum} href={`/eign/${s.fastnum}`} className="vm-card vm-card-elevated">
                <div style={{ fontFamily: "var(--font-display)", fontSize: "1.05rem", fontWeight: 500 }}>
                  {s.property?.heimilisfang || `Fastnum ${s.fastnum}`}
                </div>
                <div style={{ fontSize: "0.85rem", color: "var(--vm-ink-muted)", marginTop: "0.25rem" }}>
                  {s.property?.postnr} {s.property?.postheiti} ·{" "}
                  {s.property?.canonical_code && formatSegment(s.property.canonical_code)}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState text="Þú hefur ekki vistað eignir ennþá. Leitaðu að eign og smelltu á ⭐ til að vista." />
        )}
      </section>

      <section>
        <h2 className="display" style={{ fontSize: "1.6rem", marginBottom: "1rem" }}>
          Nýleg verðmöt
        </h2>
        {valuations && valuations.length ? (
          <div className="vm-card" style={{ padding: 0, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.92rem" }}>
              <thead>
                <tr style={{ background: "var(--vm-surface-elevated)" }}>
                  <Th>Eign</Th>
                  <Th right>Verðmat</Th>
                  <Th right>Delta</Th>
                  <Th>Dags</Th>
                </tr>
              </thead>
              <tbody>
                {valuations.map((v) => {
                  const delta = v.adjusted_mean && v.baseline_mean
                    ? 100 * (v.adjusted_mean - v.baseline_mean) / v.baseline_mean
                    : null;
                  return (
                    <tr key={v.id} style={{ borderTop: "1px solid var(--vm-border)" }}>
                      <Td>
                        <Link href={`/eign/${v.fastnum}`} style={{ color: "var(--vm-ink)" }}>
                          {v.property?.heimilisfang || `Fastnum ${v.fastnum}`}
                        </Link>
                      </Td>
                      <Td right className="tabular">
                        {formatMillions(v.adjusted_mean || v.baseline_mean)}
                      </Td>
                      <Td right className="tabular">
                        {delta != null ? (
                          <span style={{ color: delta > 0 ? "var(--vm-success)" : "var(--vm-danger)" }}>
                            {delta > 0 ? "+" : ""}{delta.toFixed(1)}%
                          </span>
                        ) : "—"}
                      </Td>
                      <Td>
                        {new Date(v.created_at).toLocaleDateString("is-IS", {
                          year: "numeric", month: "short", day: "numeric",
                        })}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState text={'Engin nýleg verðmöt. Opnaðu eign og smelltu „Persónulegt mat“ til að búa til.'} />
        )}
      </section>
    </main>
  );
}

function CtaCard({ href, title, body, accent }) {
  return (
    <Link
      href={href}
      className="vm-card vm-card-elevated"
      style={{
        display: "block",
        borderLeft: accent ? "3px solid var(--vm-accent)" : "1px solid var(--vm-border)",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "1.2rem",
          fontWeight: 500,
          marginBottom: "0.5rem",
          color: "var(--vm-ink)",
        }}
      >
        {title}
      </div>
      <div style={{ color: "var(--vm-ink-muted)", fontSize: "0.9rem", lineHeight: 1.55 }}>
        {body}
      </div>
    </Link>
  );
}

function EmptyState({ text }) {
  return (
    <div
      className="vm-card"
      style={{
        textAlign: "center",
        padding: "2.5rem 1.5rem",
        color: "var(--vm-ink-faint)",
        fontSize: "0.95rem",
        fontStyle: "italic",
      }}
    >
      {text}
    </div>
  );
}

function Th({ children, right }) {
  return (
    <th style={{
      textAlign: right ? "right" : "left",
      padding: "0.75rem 1rem",
      fontSize: "0.75rem",
      fontWeight: 600,
      color: "var(--vm-ink-muted)",
      letterSpacing: "0.05em",
      textTransform: "uppercase",
    }}>{children}</th>
  );
}
function Td({ children, right, className }) {
  return (
    <td className={className} style={{
      textAlign: right ? "right" : "left",
      padding: "0.7rem 1rem",
      color: "var(--vm-ink)",
    }}>{children}</td>
  );
}
