import { formatMillions, formatKr, formatPercent } from "@/lib/format";

export default function PredictionCard({ prediction, fasteignamat }) {
  const mean = prediction.real_pred_mean;
  const lo95 = prediction.real_pred_lo95;
  const hi95 = prediction.real_pred_hi95;
  const lo80 = prediction.real_pred_lo80;
  const hi80 = prediction.real_pred_hi80;

  const width = hi95 - lo95;
  const pct = (v) => ((v - lo95) / width) * 100;

  // Delta vs gildandi fasteignamat (fasteignamat is in thús.kr, mean in kr)
  let deltaPct = null;
  if (fasteignamat && fasteignamat > 0) {
    const matReal = fasteignamat * 1000;
    deltaPct = (mean - matReal) / matReal;
  }

  return (
    <section
      className="vm-card vm-card-elevated"
      style={{
        marginBottom: "2rem",
        borderTop: "3px solid var(--vm-accent)",
        padding: "2rem 2.25rem",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "1rem",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--vm-accent)",
              fontWeight: 600,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: "0.35rem",
            }}
          >
            Verðmat í dag
          </div>
          <div
            className="display tabular"
            style={{
              fontSize: "clamp(2.5rem, 5vw, 3.5rem)",
              color: "var(--vm-ink)",
              lineHeight: 1,
            }}
          >
            {formatMillions(mean, 1)}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--vm-ink-faint)",
              marginBottom: "0.25rem",
            }}
          >
            Miðgildi (q50)
          </div>
          <div className="tabular" style={{ fontWeight: 500 }}>
            {formatMillions(prediction.real_pred_median, 1)}
          </div>
        </div>
      </div>

      {/* PI bar visualization */}
      <div
        style={{
          position: "relative",
          height: 64,
          marginBottom: "1.25rem",
          marginTop: "1.5rem",
        }}
      >
        {/* 95% outer band */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: "50%",
            height: 16,
            transform: "translateY(-50%)",
            background: "var(--vm-accent-soft)",
            opacity: 0.4,
            borderRadius: 8,
          }}
        />
        {/* 80% inner band */}
        <div
          style={{
            position: "absolute",
            left: `${pct(lo80)}%`,
            width: `${pct(hi80) - pct(lo80)}%`,
            top: "50%",
            height: 16,
            transform: "translateY(-50%)",
            background: "var(--vm-accent)",
            opacity: 0.85,
            borderRadius: 8,
          }}
        />
        {/* Mean marker */}
        <div
          style={{
            position: "absolute",
            left: `${pct(mean)}%`,
            top: "50%",
            transform: "translate(-50%, -50%)",
            width: 3,
            height: 32,
            background: "var(--vm-ink)",
            borderRadius: 2,
          }}
        />
        {/* Labels */}
        <div
          className="tabular"
          style={{
            position: "absolute",
            left: 0,
            bottom: 0,
            fontSize: "0.75rem",
            color: "var(--vm-ink-faint)",
          }}
        >
          {formatMillions(lo95)}
        </div>
        <div
          className="tabular"
          style={{
            position: "absolute",
            right: 0,
            bottom: 0,
            fontSize: "0.75rem",
            color: "var(--vm-ink-faint)",
          }}
        >
          {formatMillions(hi95)}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "1rem",
          marginTop: "1rem",
        }}
      >
        <div
          style={{
            padding: "0.75rem 1rem",
            background: "rgba(200, 113, 70, 0.06)",
            borderRadius: 8,
          }}
        >
          <div
            style={{
              fontSize: "0.72rem",
              color: "var(--vm-accent)",
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              marginBottom: "0.2rem",
            }}
          >
            80% vissubil
          </div>
          <div className="tabular" style={{ fontWeight: 500 }}>
            {formatMillions(lo80)} – {formatMillions(hi80)}
          </div>
        </div>
        <div
          style={{
            padding: "0.75rem 1rem",
            background: "rgba(229, 183, 158, 0.22)",
            borderRadius: 8,
          }}
        >
          <div
            style={{
              fontSize: "0.72rem",
              color: "var(--vm-accent)",
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              marginBottom: "0.2rem",
            }}
          >
            95% vissubil
          </div>
          <div className="tabular" style={{ fontWeight: 500 }}>
            {formatMillions(lo95)} – {formatMillions(hi95)}
          </div>
        </div>
      </div>

      {deltaPct !== null && (
        <div
          style={{
            marginTop: "1.25rem",
            padding: "0.9rem 1.1rem",
            background: "var(--vm-surface)",
            borderRadius: 8,
            fontSize: "0.95rem",
            color: "var(--vm-ink-muted)",
          }}
        >
          Spáin er{" "}
          <strong
            style={{
              color:
                deltaPct > 0
                  ? "var(--vm-success)"
                  : deltaPct < 0
                  ? "var(--vm-danger)"
                  : "var(--vm-ink)",
            }}
          >
            {deltaPct > 0 ? "+" : ""}
            {formatPercent(deltaPct, 1)}
          </strong>{" "}
          miðað við gildandi fasteignamat ({formatMillions(fasteignamat * 1000, 1)}).
        </div>
      )}

      <div
        style={{
          marginTop: "1rem",
          fontSize: "0.78rem",
          color: "var(--vm-ink-faint)",
          fontFamily: "var(--font-mono)",
        }}
      >
        model: {prediction.model_version} · {prediction.calibration_version} ·
        segment: {prediction.segment} · {prediction.predicted_at}
      </div>
    </section>
  );
}
