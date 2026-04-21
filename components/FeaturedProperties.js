import Link from "next/link";
import Image from "next/image";
import { formatSegment, formatM2, formatMillions } from "@/lib/format";

export default function FeaturedProperties({ items }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: "1.5rem",
      }}
    >
      {items.map((p) => (
        <Link
          key={p.fastnum}
          href={`/eign/${p.fastnum}`}
          style={{ display: "block" }}
        >
          <div
            className="vm-card-elevated"
            style={{
              background: "var(--vm-surface-elevated)",
              border: "1px solid var(--vm-border)",
              borderRadius: 10,
              overflow: "hidden",
              transition: "transform 140ms ease, box-shadow 140ms ease",
            }}
          >
            {p.first_photo_url ? (
              <div
                style={{
                  position: "relative",
                  width: "100%",
                  height: 200,
                  background: "var(--vm-surface)",
                }}
              >
                <Image
                  src={p.first_photo_url}
                  alt={p.heimilisfang}
                  fill
                  style={{ objectFit: "cover" }}
                  unoptimized
                />
              </div>
            ) : (
              <div
                style={{
                  height: 200,
                  background: "var(--vm-surface)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--vm-ink-faint)",
                }}
              >
                engin mynd
              </div>
            )}
            <div style={{ padding: "1.1rem 1.25rem" }}>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "1.1rem",
                  fontWeight: 500,
                  marginBottom: "0.25rem",
                  color: "var(--vm-ink)",
                }}
              >
                {p.heimilisfang}
              </div>
              <div
                style={{
                  fontSize: "0.85rem",
                  color: "var(--vm-ink-muted)",
                  marginBottom: "0.75rem",
                }}
              >
                {p.postnr} {p.postheiti} · {formatSegment(p.canonical_code)} ·{" "}
                {formatM2(p.einflm)}
              </div>
              {p.prediction && (
                <div
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "1.35rem",
                    fontWeight: 500,
                    color: "var(--vm-primary)",
                  }}
                  className="tabular"
                >
                  {formatMillions(p.prediction.real_pred_mean)}
                </div>
              )}
              {p.prediction && (
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--vm-ink-muted)",
                  }}
                  className="tabular"
                >
                  {formatMillions(p.prediction.real_pred_lo80)} –{" "}
                  {formatMillions(p.prediction.real_pred_hi80)} (80% bil)
                </div>
              )}
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
