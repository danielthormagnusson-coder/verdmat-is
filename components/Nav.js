import Link from "next/link";

export default function Nav() {
  return (
    <header
      style={{
        borderBottom: "1px solid var(--vm-border)",
        background: "rgba(245, 240, 230, 0.85)",
        backdropFilter: "blur(10px)",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      <nav
        className="vm-container"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "18px 24px",
        }}
      >
        <Link
          href="/"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.45rem",
            fontWeight: 500,
            letterSpacing: "-0.02em",
            color: "var(--vm-ink)",
          }}
        >
          verdmat<span style={{ color: "var(--vm-accent)" }}>.is</span>
        </Link>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1.75rem",
            fontSize: "0.95rem",
          }}
        >
          <Link href="/" style={{ color: "var(--vm-ink-muted)" }}>
            Verðmat
          </Link>
          <Link href="/markadur" style={{ color: "var(--vm-ink-muted)" }}>
            Markaður
          </Link>
          <Link href="/um" style={{ color: "var(--vm-ink-muted)" }}>
            Um
          </Link>
        </div>
      </nav>
    </header>
  );
}
