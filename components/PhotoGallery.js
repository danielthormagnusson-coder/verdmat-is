"use client";

import { useState } from "react";
import Image from "next/image";

export default function PhotoGallery({ photos, title }) {
  const [active, setActive] = useState(0);
  const safe = (photos || []).slice(0, 6);
  if (!safe.length) {
    return (
      <div
        style={{
          height: 420,
          borderRadius: 10,
          background: "var(--vm-surface)",
          border: "1px solid var(--vm-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--vm-ink-faint)",
        }}
      >
        Engar myndir í gagnagrunni
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          position: "relative",
          width: "100%",
          height: 420,
          borderRadius: 10,
          overflow: "hidden",
          background: "var(--vm-surface)",
          border: "1px solid var(--vm-border)",
        }}
      >
        <Image
          src={safe[active]}
          alt={title || "Eign"}
          fill
          style={{ objectFit: "cover" }}
          unoptimized
          priority
        />
      </div>
      {safe.length > 1 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${Math.min(safe.length, 6)}, 1fr)`,
            gap: "0.5rem",
            marginTop: "0.5rem",
          }}
        >
          {safe.map((url, i) => (
            <button
              key={i}
              onClick={() => setActive(i)}
              aria-label={`Mynd ${i + 1} af ${safe.length}`}
              aria-pressed={active === i}
              style={{
                position: "relative",
                height: 68,
                borderRadius: 6,
                overflow: "hidden",
                border:
                  active === i
                    ? "2px solid var(--vm-primary)"
                    : "1px solid var(--vm-border)",
                cursor: "pointer",
                padding: 0,
                background: "var(--vm-surface)",
              }}
            >
              <Image src={url} alt="" fill style={{ objectFit: "cover" }} unoptimized />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
