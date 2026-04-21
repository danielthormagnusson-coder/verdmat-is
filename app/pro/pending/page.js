export const metadata = {
  title: "Aðgangur bíður virkjunar — verdmat.is",
};

export default function Pending() {
  return (
    <main
      className="vm-container-narrow"
      style={{ padding: "5rem 0 6rem", maxWidth: 560 }}
    >
      <p
        style={{
          fontSize: "0.85rem",
          color: "var(--vm-neutral)",
          fontWeight: 600,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          marginBottom: "0.75rem",
        }}
      >
        AÐGANGUR BÍÐUR
      </p>
      <h1 className="display" style={{ fontSize: "2.2rem", marginBottom: "1rem" }}>
        Aðgangur hefur ekki verið virkjaður
      </h1>
      <p style={{ color: "var(--vm-ink-muted)", lineHeight: 1.6, marginBottom: "2rem" }}>
        Þú ert innskráður en netfangið þitt er ekki í Pro-notendalistanum.
        Þetta gerist stundum þegar boð hefur ekki enn verið virkjað hjá
        stjórnanda. Hafðu samband ef þú heldur þetta sé mistök.
      </p>
      <a href="/" className="vm-btn-secondary">
        Aftur á forsíðu
      </a>
    </main>
  );
}
