export const metadata = {
  title: "Um verdmat.is",
  description: "Um vettvanginn — gögn, aðferðafræði, heimildir.",
};

export default function AboutPage() {
  return (
    <main
      className="vm-container-narrow"
      style={{ padding: "3rem 0 4rem" }}
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
        UM VETTVANGINN
      </p>
      <h1
        className="display"
        style={{ fontSize: "2.75rem", marginBottom: "1rem" }}
      >
        Hvað er verdmat.is?
      </h1>
      <div className="prose-vm" style={{ fontSize: "1.05rem" }}>
        <p>
          <strong>verdmat.is</strong> er óháður verðmatsvettvangur fyrir
          íslenskan fasteignamarkað, byggður á opinberum þinglýstum
          kaupsamningum og AI-módelum kvarðaðum á raunverulegum sölum.
        </p>

        <h2
          className="display"
          style={{ fontSize: "1.5rem", marginTop: "2rem", marginBottom: "0.75rem" }}
        >
          Gögn
        </h2>
        <p>
          Safnið inniheldur <strong>124.835 eignir</strong> með tengdum HMS
          fasteignaskrárupplýsingum, <strong>173.081 þinglýstar sölur</strong>
          (2006–2026) úr kaupskrá HMS, <strong>1.153.063 myndir</strong> úr
          auglýsingasögum, og <strong>374 mánaðargildi</strong> af VNV-vísitölu
          frá Hagstofunni (VIS01004).
        </p>

        <h2
          className="display"
          style={{ fontSize: "1.5rem", marginTop: "2rem", marginBottom: "0.75rem" }}
        >
          Módelið
        </h2>
        <p>
          Verðmat er framleitt af LightGBM quantile-regression módelum (6 módel
          fyrir hverja fjölskyldu: mean + q025/q10/q50/q90/q975) kvarðaðum per
          segment með empirísku stretch-factor á sérstakri holdout-safn.
          Núverandi útgáfa er <code className="vm-mono">iter3v2 ·
          iter3v2_segcal_v1</code>.
        </p>

        <h2
          className="display"
          style={{ fontSize: "1.5rem", marginTop: "2rem", marginBottom: "0.75rem" }}
        >
          Verðbólguleiðrétting
        </h2>
        <p>
          Öll verð eru CPI-deflated (raunvirði miðað við VNV verðtryggingar) til
          að nominal-verðsskekkjur yfir 20 ára tímabil séu ekki ranglega
          attribute-aðar á eiginleika eignanna. Birting á UI er í
          nominal-krónum í dagsins verðlagi (raun × CPI-factor_now).
        </p>

        <h2
          className="display"
          style={{ fontSize: "1.5rem", marginTop: "2rem", marginBottom: "0.75rem" }}
        >
          Fyrirvari
        </h2>
        <p>
          Verðmat er AI-spá byggð á sögulegum opinberum gögnum og eru ekki
          löggilt fasteignamat skv. lögum. Notið á eigin ábyrgð og leitið til
          löggilts fasteignamatsmanns fyrir bindandi mat — sérstaklega í
          bankaviðskiptum eða eignaskiptum.
        </p>
      </div>
    </main>
  );
}
