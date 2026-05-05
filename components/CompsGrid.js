import Link from "next/link";
import Image from "next/image";
import {
  formatMillions,
  formatM2,
  formatSegment,
  formatRelativeDate,
} from "@/lib/format";

function similarityLabel(score) {
  if (score < 1.2) return "Mjög sambærileg";
  if (score < 2.5) return "Sambærileg";
  return "Svipuð";
}

export default function CompsGrid({ comps }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: "1.25rem",
      }}
    >
      {comps.map((c) => {
        const p = c.prop || {};
        return (
          <Link key={c.comp_fastnum} href={`/eign/${c.comp_fastnum}`}>
            <div
              className="vm-card-elevated"
              style={{
                background: "var(--vm-surface-elevated)",
                border: "1px solid var(--vm-border)",
                borderRadius: 10,
                overflow: "hidden",
                display: "flex",
                flexDirection: "column",
                height: "100%",
              }}
            >
              {p.first_photo_url ? (
                <div
                  style={{
                    position: "relative",
                    width: "100%",
                    height: 160,
                    background: "var(--vm-surface)",
                  }}
                >
                  <Image
                    src={p.first_photo_url}
                    alt={p.heimilisfang || ""}
                    fill
                    sizes="(max-width: 768px) 100vw, 33vw"
                    style={{ objectFit: "cover" }}
                  />
                </div>
              ) : (
                <div
                  style={{
                    height: 160,
                    background: "var(--vm-surface)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--vm-ink-faint)",
                    fontSize: "0.85rem",
                  }}
                >
                  engin mynd
                </div>
              )}
              <div
                style={{
                  padding: "1rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.35rem",
                  flex: 1,
                }}
              >
                <div
                  style={{
                    fontWeight: 500,
                    color: "var(--vm-ink)",
                    fontSize: "1rem",
                  }}
                >
                  {p.heimilisfang || `Fastnum ${c.comp_fastnum}`}
                </div>
                <div
                  style={{
                    fontSize: "0.82rem",
                    color: "var(--vm-ink-muted)",
                  }}
                >
                  {p.postnr || ""} {p.postheiti || ""}
                  {p.canonical_code ? ` · ${formatSegment(p.canonical_code)}` : ""}
                  {p.einflm ? ` · ${formatM2(p.einflm)}` : ""}
                  {p.byggar ? ` · ${Math.round(p.byggar)}` : ""}
                </div>
                <div
                  style={{
                    marginTop: "auto",
                    paddingTop: "0.5rem",
                    borderTop: "1px solid var(--vm-border)",
                  }}
                >
                  <div
                    className="tabular"
                    style={{
                      fontWeight: 500,
                      color: "var(--vm-primary)",
                    }}
                  >
                    Seld {formatMillions(c.last_sale_price_real)}
                  </div>
                  <div
                    style={{
                      fontSize: "0.78rem",
                      color: "var(--vm-ink-muted)",
                    }}
                  >
                    {formatRelativeDate(c.last_sale_date)} ·{" "}
                    {similarityLabel(c.distance_score)}
                  </div>
                </div>
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
