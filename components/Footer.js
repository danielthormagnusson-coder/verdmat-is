export default function Footer() {
  return (
    <footer
      style={{
        marginTop: "5rem",
        borderTop: "1px solid var(--vm-border)",
        background: "var(--vm-surface)",
        padding: "3rem 0 2rem",
      }}
    >
      <div className="vm-container">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "2.5rem",
          }}
        >
          <div>
            <h4
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "1.05rem",
                marginBottom: "0.75rem",
                color: "var(--vm-ink)",
              }}
            >
              Um verdmat.is
            </h4>
            <p
              style={{
                fontSize: "0.9rem",
                lineHeight: 1.6,
                color: "var(--vm-ink-muted)",
              }}
            >
              Óháður verðmatsvettvangur byggður á opinberum þinglýstum
              kaupsamningum og AI-módelum kvarðaðum á íslenska markaðnum.
            </p>
          </div>
          <div>
            <h4
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "1.05rem",
                marginBottom: "0.75rem",
                color: "var(--vm-ink)",
              }}
            >
              Gagnagrunnur
            </h4>
            <ul
              style={{
                listStyle: "none",
                padding: 0,
                margin: 0,
                fontSize: "0.9rem",
                color: "var(--vm-ink-muted)",
                lineHeight: 1.9,
              }}
            >
              <li>HMS fasteignaskrá</li>
              <li>Kaupskrá (þinglýst verð)</li>
              <li>Staðfangaskrá</li>
              <li>Hagstofan (VNV)</li>
            </ul>
          </div>
          <div>
            <h4
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "1.05rem",
                marginBottom: "0.75rem",
                color: "var(--vm-ink)",
              }}
            >
              Tæki
            </h4>
            <ul
              style={{
                listStyle: "none",
                padding: 0,
                margin: 0,
                fontSize: "0.9rem",
                color: "var(--vm-ink-muted)",
                lineHeight: 1.9,
              }}
            >
              <li>Módel: iter3v2 · seg-calibrated</li>
              <li>Uppfært: apríl 2026</li>
              <li>124.835 eignir í gagnagrunni</li>
            </ul>
          </div>
        </div>
        <div
          style={{
            marginTop: "2.5rem",
            paddingTop: "1.5rem",
            borderTop: "1px solid var(--vm-border)",
            fontSize: "0.82rem",
            color: "var(--vm-ink-faint)",
            lineHeight: 1.6,
          }}
        >
          Verðmat er AI-spá byggð á opinberum gögnum og eru ekki löggilt
          fasteignamat skv. lögum. Notið á eigin ábyrgð og leitið til löggilts
          fasteignamatsmanns fyrir bindandi mat.
        </div>
      </div>
    </footer>
  );
}
