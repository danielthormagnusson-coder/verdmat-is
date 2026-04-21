export const metadata = {
  title: "Pro aðgangur — verdmat.is",
};

const CONTACT_EMAIL = "hello@verdmat.is";

export default function LoginPage() {
  return (
    <main
      className="vm-container-narrow"
      style={{ padding: "4rem 0 6rem", maxWidth: 560 }}
    >
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
        PRO AÐGANGUR
      </p>
      <h1
        className="display"
        style={{ fontSize: "2.5rem", marginBottom: "0.75rem" }}
      >
        Pro útgáfan er á leiðinni
      </h1>
      <p
        style={{
          color: "var(--vm-ink-muted)",
          marginBottom: "1.5rem",
          lineHeight: 1.6,
          fontSize: "1.05rem",
        }}
      >
        Pro-útgáfan er í þróun og verður opnuð með boði á næstu vikum. Hún er
        gerð fyrir fasteignasala og bankastarfsmenn sem þurfa að búa til
        persónuleg verðmöt með spurningalista, vista eignir, og flytja út
        verðmötin á PDF.
      </p>

      <div
        className="vm-card vm-card-elevated"
        style={{ marginBottom: "1.5rem", padding: "1.5rem 1.75rem" }}
      >
        <div
          style={{
            fontSize: "0.75rem",
            color: "var(--vm-accent)",
            fontWeight: 600,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            marginBottom: "0.5rem",
          }}
        >
          Snemma-boð
        </div>
        <h2
          className="display"
          style={{ fontSize: "1.3rem", marginBottom: "0.75rem" }}
        >
          Viltu prófa fyrstur?
        </h2>
        <p
          style={{
            color: "var(--vm-ink-muted)",
            marginBottom: "1.25rem",
            lineHeight: 1.6,
          }}
        >
          Ef þú ert fasteignasali eða bankastarfsmaður og hefur áhuga á að
          prófa Pro-útgáfuna sem snemma notandi, sendu mér póst og ég bæti þér
          í boðslistann.
        </p>
        <a
          href={`mailto:${CONTACT_EMAIL}?subject=Pro%20sn%C3%A6ma-bo%C3%B0%20verdmat.is`}
          className="vm-btn"
          style={{ display: "inline-block", textDecoration: "none" }}
        >
          Senda póst
        </a>
      </div>

      <div
        style={{
          fontSize: "0.9rem",
          color: "var(--vm-ink-muted)",
          lineHeight: 1.6,
        }}
      >
        Í millitíðinni er grunn-útgáfan af verdmat.is opin öllum — leitaðu að
        eign á{" "}
        <a href="/" style={{ color: "var(--vm-primary)" }}>
          forsíðunni
        </a>{" "}
        eða skoðaðu{" "}
        <a href="/markadur" style={{ color: "var(--vm-primary)" }}>
          markaðsyfirlitið
        </a>
        .
      </div>
    </main>
  );
}
