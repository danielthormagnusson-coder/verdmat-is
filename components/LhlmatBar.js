// Lhlmat stacked-bar — Path C A2.
// Renders a two-segment horizontal bar showing land share vs structure share
// of the HMS fasteignamat. Hidden when lhlmat is null.
//
// `lhlmat` is stored as a ratio 0..1 per the 2026-05-18 migration. Defensive
// clamp keeps display sane if Phase D ever writes outside that range.

export default function LhlmatBar({ lhlmat }) {
  if (lhlmat == null) return null;
  const land = Math.max(0, Math.min(1, Number(lhlmat)));
  if (Number.isNaN(land)) return null;
  const structure = 1 - land;
  const landPct = Math.round(land * 100);
  const structurePct = 100 - landPct;

  return (
    <div
      style={{
        marginBottom: "0.9rem",
        fontSize: "0.78rem",
        color: "var(--vm-ink-muted)",
      }}
    >
      <div
        style={{
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "var(--vm-ink-faint)",
          marginBottom: "0.3rem",
          fontSize: "0.7rem",
        }}
      >
        Lóð / mannvirki
      </div>
      <div
        style={{
          display: "flex",
          height: 8,
          borderRadius: 4,
          overflow: "hidden",
          background: "var(--vm-border)",
          marginBottom: "0.3rem",
        }}
        aria-label={`Lóðarhluti ${landPct}%, mannvirki ${structurePct}%`}
      >
        <div
          style={{
            width: `${land * 100}%`,
            background: "var(--vm-accent-soft, var(--vm-accent))",
            opacity: 0.85,
          }}
        />
        <div
          style={{
            width: `${structure * 100}%`,
            background: "var(--vm-primary, var(--vm-ink))",
            opacity: 0.85,
          }}
        />
      </div>
      <div className="tabular">
        {landPct}% lóð · {structurePct}% mannvirki
      </div>
    </div>
  );
}
