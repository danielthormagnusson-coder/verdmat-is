import { formatKr, formatDate, formatM2, formatMillions } from "@/lib/format";

export default function SalesHistoryTable({ rows }) {
  return (
    <div
      className="vm-card"
      style={{ padding: 0, overflow: "hidden", background: "var(--vm-surface)" }}
    >
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.9rem",
        }}
      >
        <thead>
          <tr style={{ background: "var(--vm-surface-elevated)" }}>
            <Th>Dags</Th>
            <Th right>Verð (rauntala)</Th>
            <Th right>Verð (nominal)</Th>
            <Th right>Stærð</Th>
            <Th right>Byggt</Th>
            <Th>Staða</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const excluded = r.onothaefur === 1;
            return (
              <tr
                key={i}
                style={{
                  borderTop: "1px solid var(--vm-border)",
                  opacity: excluded ? 0.55 : 1,
                  fontStyle: excluded ? "italic" : "normal",
                }}
              >
                <Td>{formatDate(r.thinglystdags)}</Td>
                <Td right className="tabular">
                  {formatMillions(r.kaupverd_real)}
                </Td>
                <Td right className="tabular">
                  {formatKr(r.kaupverd_nominal * 1000)}
                </Td>
                <Td right>{formatM2(r.einflm_at_sale)}</Td>
                <Td right>{r.byggar_at_sale ? Math.round(r.byggar_at_sale) : "—"}</Td>
                <Td>
                  {excluded ? (
                    <span
                      className="vm-badge vm-badge-neutral"
                      style={{ fontSize: "0.68rem" }}
                    >
                      ónothæfur
                    </span>
                  ) : (
                    <span
                      className="vm-badge vm-badge-cold"
                      style={{
                        fontSize: "0.68rem",
                        background: "rgba(93, 127, 86, 0.12)",
                        color: "var(--vm-success)",
                      }}
                    >
                      arm's-length
                    </span>
                  )}
                </Td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children, right }) {
  return (
    <th
      style={{
        textAlign: right ? "right" : "left",
        padding: "0.75rem 1rem",
        fontSize: "0.75rem",
        fontWeight: 600,
        color: "var(--vm-ink-muted)",
        letterSpacing: "0.05em",
        textTransform: "uppercase",
      }}
    >
      {children}
    </th>
  );
}

function Td({ children, right, className }) {
  return (
    <td
      className={className}
      style={{
        textAlign: right ? "right" : "left",
        padding: "0.7rem 1rem",
        color: "var(--vm-ink)",
      }}
    >
      {children}
    </td>
  );
}
